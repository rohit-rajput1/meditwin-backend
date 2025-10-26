from fastapi import UploadFile, BackgroundTasks
from .process import process_upload
from .utils import create_file_id

async def file_upload(file: UploadFile, background=False, background_tasks: BackgroundTasks = None):
    """
    Entry Point for API and If background=True, run in FastAPI BackgroundTasks
    """
    try:
        file_id = create_file_id()
        if background and background_tasks:
            # Create a copy of file content for background task
            content = await file.read()
            await file.seek(0)
            background_tasks.add_task(process_upload, file, file_id, content)
            return file_id
        result_file_id = await process_upload(file, file_id)
        return result_file_id
    except Exception as e:
        raise RuntimeError(f"File upload failed: {e}")