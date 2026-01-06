# Security Policy

## Reporting Security Vulnerabilities

If you discover a security vulnerability in this project, please report it by creating a private security advisory or contacting the maintainers directly. Do not open public issues for security vulnerabilities.

## Secret Management & Token Security

### Environment Variables

This project uses environment variables to store sensitive information such as API tokens and credentials. **Never commit `.env` files containing real secrets to version control.**

#### Best Practices

1. **Use `.env.example` Templates**
   - Template files (`.env.example`) show required variables without exposing actual values
   - Copy the template and fill in your own values: `cp .env.example .env`
   - The `.env` file is automatically gitignored

2. **Token Formats**
   - GitHub Personal Access Tokens (classic): `ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`
   - GitHub OAuth Tokens: `gho_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`
   - GitHub Fine-grained Tokens: `github_pat_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`

3. **Principle of Least Privilege**
   - Grant tokens only the minimum scopes/permissions required
   - Use fine-grained tokens with repository-specific access when possible
   - Regularly audit token permissions

### Token Rotation

**Tokens should be rotated regularly to minimize risk.**

- **Recommended Schedule**: Every 90 days for production tokens
- **Immediate Rotation Required** if:
  - Token is accidentally exposed or committed to version control
  - Token is found in logs, error messages, or debugging output
  - Suspicious activity is detected on the account
  - Team member with token access leaves the project
  - System security is potentially compromised

#### How to Rotate Tokens

1. **Generate a new token** with the same permissions as the old one
   - GitHub: Settings > Developer settings > Personal access tokens
   - URL: https://github.com/settings/tokens

2. **Update all systems** using the old token with the new token
   - Local development: Update your `.env` file
   - CI/CD: Update GitHub Secrets or environment variables
   - Production: Update secret management system (e.g., AWS Secrets Manager, HashiCorp Vault)

3. **Revoke the old token** immediately after updating all systems
   - GitHub: Settings > Developer settings > Personal access tokens > Delete

4. **Verify** that all systems are working with the new token

### What to Do If a Token Is Exposed

**If you accidentally commit a secret to git:**

1. **Revoke the token immediately**
   - GitHub: https://github.com/settings/tokens
   - Treat this as a critical security incident

2. **Generate a new token** with fresh credentials

3. **Update your local `.env` file** with the new token

4. **Remove the secret from git history**
   - For recent commits not yet pushed: `git reset --soft HEAD~1`
   - For pushed commits: Use tools like `git-filter-repo` or `BFG Repo-Cleaner`
   - **Coordinate with team** before rewriting shared git history
   - Consider the repository compromised if publicly accessible

5. **Monitor for suspicious activity**
   - Review GitHub account activity
   - Check for unauthorized API usage
   - Review repository access logs

### CI/CD and Production Environments

**Never store secrets in `.env` files in CI/CD or production environments.**

#### Recommended Approaches

1. **GitHub Actions**
   - Use GitHub Secrets: Repository Settings > Secrets and variables > Actions
   - Access via: `${{ secrets.SECRET_NAME }}`
   - Never log secret values

2. **Production Systems**
   - Use dedicated secret management services:
     - AWS Secrets Manager
     - HashiCorp Vault
     - Azure Key Vault
     - Google Cloud Secret Manager
   - Use environment-specific service accounts with minimal permissions

3. **Environment Separation**
   - Use different tokens for development, staging, and production
   - Revoke development tokens immediately if they touch production data
   - Never use production tokens in local development

### Code Review Checklist

Before committing or merging code, verify:

- [ ] No hardcoded secrets in code
- [ ] No `.env` files with real secrets committed
- [ ] No tokens in comments or documentation
- [ ] No secrets in error messages or logs
- [ ] `.env.example` contains only placeholder values
- [ ] Sensitive configuration uses environment variables

### Gitignore Coverage

The repository uses comprehensive patterns to prevent accidental secret commits:

```gitignore
# Root-level .env files
.env
.env.local
.env.*.local

# .env files in any subdirectory
**/.env
**/.env.local
**/.env.*

# Exception: Allow .env.example templates
!**/.env.example
!.env.example
```

Verify protection before committing:
```bash
# Check if a file would be ignored
git check-ignore -v .auto-claude/.env

# List all tracked files matching .env pattern
git ls-files | grep -E '\.env($|\.)'
```

### Additional Resources

- [GitHub Token Security Best Practices](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens)
- [OWASP Secrets Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html)
- [git-filter-repo Documentation](https://github.com/newren/git-filter-repo)

## Version History

- **2026-01-06**: Initial security documentation created addressing token exposure risk
