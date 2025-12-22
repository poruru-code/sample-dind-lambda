function append_container_name(tag, timestamp, record)
    local modified = false

    -- 1. 既存の container_name があり、先頭が '/' なら削除
    if record["container_name"] ~= nil and string.sub(record["container_name"], 1, 1) == "/" then
        record["container_name"] = string.sub(record["container_name"], 2)
        modified = true
    end

    -- 2. container_name がない場合、タグ "lambda.<name>" から抽出
    if record["container_name"] == nil then
        local s, e = string.find(tag, "lambda%.")
        if s == 1 then
            local name = string.sub(tag, e + 1)
            if name ~= nil and name ~= "" then
                record["container_name"] = name
                modified = true
            end
        end
    end

    if modified then
        return 1, timestamp, record
    else
        return 0, 0, 0
    end
end
