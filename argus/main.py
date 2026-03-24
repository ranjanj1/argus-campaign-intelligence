from argus.launcher import create_app

# Single app instance — imported by uvicorn and by tests
app = create_app()
