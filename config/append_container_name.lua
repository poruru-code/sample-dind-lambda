function append_container_name(tag, timestamp, record)
    -- Check if container_name is already present
    if record["container_name"] ~= nil then
        return 0, 0, 0
    end

    -- Extract name from tag "lambda.<name>"
    local s, e = string.find(tag, "lambda%.")
    if s == 1 then
        local name = string.sub(tag, e + 1)
        if name ~= nil and name ~= "" then
            record["container_name"] = name
            return 1, timestamp, record
        end
    end
    return 0, 0, 0
end
