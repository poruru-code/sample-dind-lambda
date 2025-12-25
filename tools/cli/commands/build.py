import docker
from tools.generator import main as generator
from tools.cli import config as cli_config
from tools.cli.core import logging

# ESB Lambda ベースイメージ用のディレクトリ
RUNTIME_DIR = cli_config.PROJECT_ROOT / "tools" / "generator" / "runtime"
BASE_IMAGE_TAG = "esb-lambda-base:latest"


def build_base_image(no_cache=False):
    """ESB Lambda ベースイメージをビルドする"""
    client = docker.from_env()
    dockerfile_path = RUNTIME_DIR / "Dockerfile.base"

    if not dockerfile_path.exists():
        logging.warning(f"Base Dockerfile not found: {dockerfile_path}")
        return False

    logging.step("Building base image...")
    print(f"  • Building {logging.highlight(BASE_IMAGE_TAG)} ...", end="", flush=True)

    try:
        client.images.build(
            path=str(RUNTIME_DIR),
            dockerfile="Dockerfile.base",
            tag=BASE_IMAGE_TAG,
            nocache=no_cache,
            rm=True,
        )
        print(f" {logging.Color.GREEN}✅{logging.Color.END}")
        return True
    except Exception as e:
        print(f" {logging.Color.RED}❌{logging.Color.END}")
        logging.error(f"Base image build failed: {e}")
        return False


def _extract_function_name_from_dockerfile(dockerfile_path) -> str | None:
    """Dockerfile から FunctionName を抽出する"""
    try:
        with open(dockerfile_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("# FunctionName:"):
                    return line.split(":", 1)[1].strip()
    except Exception:
        pass
    return None


def build_function_images(no_cache=False, verbose=False):
    """
    生成されたDockerfileを見つけてイメージをビルドする
    """
    client = docker.from_env()
    functions_dir = cli_config.E2E_DIR / "functions"

    logging.step("Building function images...")

    if not functions_dir.exists():
        logging.warning(f"Functions directory {functions_dir} not found.")
        return

    # functionsディレクトリ以下のDockerfileを探索
    for dockerfile in sorted(functions_dir.rglob("Dockerfile")):
        # Dockerfile から FunctionName を抽出
        function_name = _extract_function_name_from_dockerfile(dockerfile)
        if not function_name:
            logging.warning(f"FunctionName not found in {dockerfile}, skipping.")
            continue

        image_tag = f"{function_name}:latest"

        print(f"  • Building {logging.highlight(image_tag)} ...", end="", flush=True)
        try:
            # ビルドコンテキストを PROJECT_ROOT に設定し、
            # Dockerfile の相対パスを PROJECT_ROOT から計算する
            relative_dockerfile = dockerfile.relative_to(cli_config.PROJECT_ROOT).as_posix()

            client.images.build(
                path=str(cli_config.PROJECT_ROOT),
                dockerfile=relative_dockerfile,
                tag=image_tag,
                nocache=no_cache,
                rm=True,
            )
            print(f" {logging.Color.GREEN}✅{logging.Color.END}")
        except Exception as e:
            print(f" {logging.Color.RED}❌{logging.Color.END}")
            if verbose:
                logging.error(f"Build failed for {image_tag}: {e}")
                raise
            else:
                logging.error(f"Build failed for {image_tag}. Use --verbose for details.")
                # Non-verbose: exit or raise without trace?
                # CLI usually should stop on error.
                import sys

                sys.exit(1)


def run(args):
    dry_run = getattr(args, "dry_run", False)
    verbose = getattr(args, "verbose", False)

    if dry_run:
        logging.info("Running in DRY-RUN mode. No files will be written, no images built.")

    # 1. 設定ファイル生成 (Phase 1 Generator)
    logging.step("Generating configurations...")
    logging.info(f"Using template: {logging.highlight(cli_config.TEMPLATE_YAML)}")

    # Generator の設定をロード
    config_path = cli_config.E2E_DIR / "generator.yml"
    if not config_path.exists():
        config_path = cli_config.PROJECT_ROOT / "tests/fixtures/generator.yml"

    config = generator.load_config(config_path)

    # テンプレートパスを解決
    if "paths" not in config:
        config["paths"] = {}
    config["paths"]["sam_template"] = str(cli_config.TEMPLATE_YAML)

    generator.generate_files(
        config=config,
        project_root=cli_config.PROJECT_ROOT,
        dry_run=dry_run,
        verbose=verbose,
    )

    if dry_run:
        logging.success("Dry-run complete. Exiting.")
        return

    logging.success("Configurations generated.")

    # 2. ベースイメージビルド
    no_cache = getattr(args, "no_cache", False)

    if not build_base_image(no_cache=no_cache):
        import sys

        sys.exit(1)

    # 3. Lambda関数イメージビルド
    build_function_images(no_cache=no_cache, verbose=verbose)

    logging.success("Build complete.")
