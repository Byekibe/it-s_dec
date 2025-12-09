# 1. High-Level Project Summary

## Overview

This project is the backend for a comprehensive, multi-tenant Software-as-a-Service (SaaS) application. It is built using **Flask** and **SQLAlchemy**.

## Core Architectural Pillars

1.  **Multi-Tenancy:** The entire system is designed around a multi-tenant architecture. Each `Tenant` is an isolated workspace. Data is automatically scoped to the current tenant, preventing data leaks between customers. The system also supports a sub-level of organization called `Stores` within each tenant.

2.  **Role-Based Access Control (RBAC):** Access to resources and actions is governed by a granular RBAC system. Users are assigned `Roles` (e.g., Owner, Admin, Manager), and `Roles` are granted specific `Permissions` (e.g., `products.create`, `users.invite`). This allows for flexible and secure permission management.

3.  **JWT Authentication:** User authentication is handled via JSON Web Tokens (JWT). The system generates `access_token` and `refresh_token` pairs upon successful login, which are used to authenticate subsequent API requests.

4.  **Service-Oriented Structure:** The application is organized into modular **Blueprints**, with each feature (e.g., Users, Stores, Billing) having its own services, repositories, schemas, and routes. This promotes separation of concerns and maintainability.

## Key Features (Implemented & Planned)

*   **Implemented:**
    *   Secure user registration and login.
    *   Automatic tenant creation for new users.
    *   Context-aware middleware for tenant and store scoping.
    *   A robust permission-checking system.

*   **Planned:**
    *   Subscription and billing management.
    *   Payment processing via M-Pesa.
    *   Usage tracking and metering.
    *   In-app and email notifications.
    *   Comprehensive testing and API documentation.
