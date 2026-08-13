def test_direct_upload_route_is_registered():
    from src.main import app

    operation = app.openapi()["paths"]["/api/v1/workspace/direct-upload"]

    assert "post" in operation
