# Security Review
## Authentication & Authorization
- **JWT:** Tokens are securely signed using HS256 with strong secrets.
- **RBAC:** Admin and standard user roles are strictly enforced in `Dependencies.py`.
- **Workspace Isolation:** Every document query strictly filters by `workspace_id`.
- **Prompt Injection:** LLM prompts are strongly typed and sanitized using LangChain templates.
- **File Upload:** Uploads are restricted to `.pdf`, `.docx`, `.txt` with a 50MB strict file size limit.

## Conclusion
The application adheres to OWASP Top 10 best practices.
