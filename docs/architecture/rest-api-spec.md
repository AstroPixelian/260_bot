# REST API Spec

_This section would contain REST API specifications if the project included a REST API._

## Current Implementation

The 360 Account Batch Creator is a desktop application that does not expose REST APIs. All functionality is accessed through the GUI interface.

### Future API Considerations

If REST API functionality is added in future versions, consider:

```yaml
openapi: 3.0.0
info:
  title: 360 Account Batch Creator API
  version: 1.0.0
  description: API for batch account management
servers:
  - url: http://localhost:8080/api/v1
    description: Local development server

# Potential endpoints for future versions:
# - POST /accounts/batch - Submit batch account creation job
# - GET /accounts/batch/{jobId} - Get batch job status
# - GET /accounts - List created accounts
```

## Current Architecture Note

The application operates as a standalone desktop GUI application without web API requirements.