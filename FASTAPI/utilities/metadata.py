# handles meta data , for now only cleaning during doc chunks storage 

def clean_metadata(meta: dict) -> dict:
    safe_meta = {}
    for k, v in meta.items():
        if isinstance(v, (str, int, float, bool)) or v is None:
            safe_meta[k] = v
        else:
            safe_meta[k] = str(v)
    return safe_meta