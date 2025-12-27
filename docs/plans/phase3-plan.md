# Phase 3: Resource Management & Self-Healing 実装プラン

## 目的 (Goal)

AWS Lambda の "Cold Shutdown" を再現し、放置されたコンテナによるメモリリークを防ぐ。
また、Gateway 再起動時（障害復旧時）に Agent 側のゾンビコンテナを一掃する **Self-Healing (自己修復)** 機能を実現する。

## 前提条件

* Gateway が「コントロールプレーン」として、リソースの削除権限を持つ。
* Agent は「データプレーン」として、コンテナの最終利用時刻を管理し、Gateway の命令に従う。

---

## 1. Protocol Buffers & Interface Definition

Agent が「どのコンテナが、いつから暇をしているか」を報告できるようにします。

### Task 1.1: `proto/agent.proto` の拡張

`ListContainers` RPC を追加します。

```protobuf
// proto/agent.proto

service AgentService {
  // ... (既存のRPC)
  
  // [NEW] 管理下の全コンテナの状態を取得
  rpc ListContainers (ListContainersRequest) returns (ListContainersResponse);
}

message ListContainersRequest {}

message ListContainersResponse {
  repeated ContainerState containers = 1;
}

message ContainerState {
  string container_id = 1;
  string function_name = 2;
  string status = 3;      // "RUNNING", "PAUSED", "STOPPED", "UNKNOWN"
  int64 last_used_at = 4; // Unix Timestamp (ナノ秒または秒)
}

```

* **Action**: 定義後、`tools/gen_proto.py` を実行して Go/Python コードを再生成。

### Task 1.2: Go Interface の更新

`services/agent/internal/runtime/interface.go` にメソッドを追加します。

```go
type ContainerRuntime interface {
    // ...
    List(ctx context.Context) ([]ContainerState, error)
}

// ContainerState 構造体も定義（Protoの生成コードを使っても良いが、内部モデルを持つのがベター）
type ContainerState struct {
    ID         string
    Name       string
    Status     string
    LastUsedAt time.Time
}

```

---

## 2. Agent Implementation (Go)

Agent 側で「最終アクセス時刻」をメモリ上に保持し、問い合わせに応答するロジックを実装します。

### Task 2.1: Access Tracker の実装 (`internal/runtime/containerd/runtime.go`)

containerd のメタデータには「最終アクセス時刻」がないため、`sync.Map` で管理します。

* **変更点**:
* `ContainerdRuntime` 構造体に `accessTracker sync.Map` を追加。
* **記録タイミング**:
* `Ensure` (Create/Start時): `Now()` を記録。
* `Ensure` (Resume時): `Now()` を記録。


* **削除タイミング**:
* `Destroy`: `sync.Map` から削除。
* `GC`: `sync.Map` から削除。





### Task 2.2: `List` メソッドの実装

全コンテナを走査し、containerd の状態と Tracker の時刻をマージします。

```go
// services/agent/internal/runtime/containerd/runtime.go

func (r *ContainerdRuntime) List(ctx context.Context) ([]ContainerState, error) {
    // 1. containerd から "namespace==esb" のコンテナ一覧を取得
    containers, _ := r.client.Containers(ctx, "namespace==esb")
    
    var states []ContainerState
    for _, c := range containers {
        // 2. タスクの状態を取得 (Running, Paused, etc)
        task, err := c.Task(ctx, nil)
        status := "STOPPED"
        if err == nil {
            s, _ := task.Status(ctx)
            status = s.Status.String()
        }

        // 3. accessTracker から時刻を取得 (なければ作成時刻等のフォールバック)
        lastUsed, ok := r.accessTracker.Load(c.ID())
        
        states = append(states, ContainerState{
            ID: c.ID(),
            Status: status,
            LastUsedAt: lastUsed,
            // ...
        })
    }
    return states, nil
}

```

### Task 2.3: API Server への結合

`services/agent/internal/api/server.go` に `ListContainers` ハンドラを実装し、Runtime の `List` を呼び出して Proto メッセージに変換して返します。

---

## 3. Gateway Implementation (Python)

Janitor（管理人）ロジックを実装し、定期的な掃除と起動時のクリーンアップを行います。

### Task 3.1: Interface Update

`services/gateway/services/lambda_invoker.py` の `InvocationBackend` Protocol に以下を追加します。

```python
class InvocationBackend(Protocol):
    # ...
    async def list_workers(self) -> List[WorkerState]: ...
    async def evict_worker(self, function_name: str, worker_id: str) -> None: ...

```

### Task 3.2: `GrpcBackend` の実装 (`services/gateway/services/grpc_backend.py`)

`ListContainers` RPC を呼び出す実装を追加します。

### Task 3.3: `Janitor` Service の実装 (`services/gateway/services/janitor.py`)

ここが Gateway のロジックの中核です。

* **Config**: `IDLE_TIMEOUT` (デフォルト 600秒), `CLEANUP_INTERVAL` (デフォルト 60秒)。
* **`cleanup_on_startup()` メソッド**:
* Gateway 起動時に呼ばれる。
* Agent から全コンテナを取得。
* **ポリシー**: 「Gateway が知らないコンテナは全て削除する」または「Paused なコンテナは全て削除する」。
* これにより、Gateway クラッシュ後のゾンビコンテナを一掃します。


* **`run_loop()` メソッド**:
* 無限ループで `await asyncio.sleep(interval)`。
* `backend.list_workers()` を取得。
* 条件 `status == PAUSED` かつ `now - last_used > IDLE_TIMEOUT` のコンテナに対して `evict_worker()` を実行。



### Task 3.4: Main 統合 (`services/gateway/main.py`)

FastAPI のライフサイクルイベントに組み込みます。

```python
# services/gateway/main.py

@asynccontextmanager
async def lifespan(app: FastAPI):
    # ... backend 初期化 ...
    
    janitor = Janitor(backend, config)
    
    # 1. 起動時クリーンアップ (ブロッキング実行で安全を確保)
    await janitor.cleanup_on_startup()
    
    # 2. 定期実行ループをバックグラウンドで開始
    asyncio.create_task(janitor.run_loop())
    
    yield
    # ...

```

---

## 4. Verification Plan (検証)

### テストシナリオ

1. **Idle Timeout Test**:
* `IDLE_TIMEOUT=5` (5秒) に設定して起動。
* 関数を実行 (Running -> Paused)。
* 5秒待つ。
* Gateway のログに `Evicting idle container` が出力され、`docker ps` (または ctr) からコンテナが消えることを確認。


2. **Startup Cleanup Test**:
* コンテナをいくつか起動した状態で、Gateway (`docker-compose restart gateway`) だけ再起動する。
* Gateway 起動直後のログで `Startup cleanup: removing X containers` が出力され、既存のゾンビコンテナが一掃されることを確認。


3. **Performance Check**:
* `ListContainers` が大量のコンテナ（例: 100個）存在する場合でも高速に応答するか（containerd API のオーバーヘッド確認）。



---

## 次のアクション

この詳細プランに基づき、**Task 1.1 (Proto定義)** から実装を開始してください。
Gateway 側の Janitor 実装は、Agent 側の `List` 機能が動いてから結合することをお勧めします。