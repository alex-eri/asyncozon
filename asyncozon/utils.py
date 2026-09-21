async def chunk_async_iterator(async_iterator, size):
    if size < 1:
        raise ValueError("Size must be at least 1")

    iterator = aiter(async_iterator)
    finished = False

    while not finished:
        chunk = []
        for _ in range(size):
            try:
                item = await anext(iterator)
                chunk.append(item)
            except StopAsyncIteration:
                finished = True
                break
        if chunk:
            yield chunk
