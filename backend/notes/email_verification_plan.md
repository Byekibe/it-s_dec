# Email Verification Implementation Plan

## Overview
This plan outlines the steps to implement the email verification flow for user accounts, ensuring that newly registered users confirm their email addresses before gaining full access to certain features. This is a crucial step in enhancing user security and ensuring valid contact information.

## Tasks

### 1. Update User Model
- **File**: `app/blueprints/users/models.py`
- **Action**: Add a new boolean field `email_verified` to the `User` model, defaulting to `False`.

### 2. Create Email Verification Token Model
- **Files**:
    - `app/blueprints/auth/models.py` (or a new `app/blueprints/auth/tokens.py` if preferred for token-related models)
    - `app/blueprints/auth/schemas.py` (for serialization/deserialization if needed)
- **Action**: Create a new SQLAlchemy model `EmailVerificationToken` with fields such as:
    - `id` (Primary Key)
    - `user_id` (Foreign Key to User)
    - `token` (Unique string for verification)
    - `expires_at` (Datetime to track token expiry)
    - `created_at` (Timestamp)

### 3. Implement Email Sending Celery Task
- **File**: `app/tasks/email_tasks.py`
- **Action**: Create a new Celery task, e.g., `send_verification_email_task`, that takes user information (e.g., email, verification link) and sends an email. This task should utilize the Flask-Mail setup.

### 4. Update AuthService to Generate and Send Token
- **File**: `app/blueprints/auth/services.py`
- **Action**:
    - Modify the `AuthService.register` method to:
        - Generate an `EmailVerificationToken` after user registration.
        - Save the token to the database.
        - Call the `send_verification_email_task` to send the verification email to the new user.
    - Add a new method, e.g., `AuthService.send_email_verification_email(user_id)`, to be called by the new `/resend-verification` endpoint.
    - Add a new method, e.g., `AuthService.verify_email(token)`, to handle token validation and mark the user as `email_verified`.

### 5. Create New API Endpoints
- **File**: `app/blueprints/auth/routes.py`
- **Action**:
    - `POST /api/v1/auth/resend-verification`:
        - Requires authentication (`@jwt_required`).
        - Triggers the `AuthService` to generate a new token and send a verification email if the user's email is not yet verified.
    - `POST /api/v1/auth/verify-email`:
        - Accepts a verification token in the request body.
        - Calls `AuthService.verify_email` to validate the token and update the user's `email_verified` status.

### 6. Add Database Migration
- **Action**: After updating the `User` model and creating the `EmailVerificationToken` model, generate a new database migration using `flask db migrate -m "Add email_verification_fields_and_table"`. Apply this migration.

### 7. Write Tests
- **File**: `tests/test_auth.py`
- **Action**: Add unit and integration tests for:
    - User registration successfully sending a verification email.
    - Resending a verification email.
    - Successfully verifying an email with a valid token.
    - Handling invalid or expired verification tokens.
    - Ensuring `email_verified` status is correctly updated.

## Dependencies / Relevant Files
- `app/blueprints/users/models.py`
- `app/blueprints/auth/models.py` (or new token file)
- `app/blueprints/auth/services.py`
- `app/blueprints/auth/routes.py`
- `app/blueprints/auth/schemas.py`
- `app/tasks/email_tasks.py`
- `app/extensions.py` (for mail extension if not already set up)
- `tests/test_auth.py`
- `requirements.txt` (ensure `Flask-Mail` and `celery` are present)
