"""
Permission constants for the RBAC system.

Permissions follow the naming convention: resource.action
These are code-defined and seeded into the database via migrations.

Usage:
    from app.core.constants import Permissions

    @require_permission(Permissions.PRODUCTS_CREATE)
    def create_product():
        ...
"""


class Permissions:
    """
    All permission constants for the application.

    Organized by resource domain.
    """

    # ========================================
    # User Management Permissions
    # ========================================
    USERS_VIEW = "users.view"           # View user list and details
    USERS_CREATE = "users.create"       # Invite/create new users
    USERS_EDIT = "users.edit"           # Edit user details
    USERS_DELETE = "users.delete"       # Deactivate/remove users
    USERS_MANAGE_ROLES = "users.manage_roles"  # Assign/revoke roles

    # ========================================
    # Tenant Management Permissions
    # ========================================
    TENANTS_VIEW = "tenants.view"       # View tenant settings
    TENANTS_EDIT = "tenants.edit"       # Edit tenant settings
    TENANTS_MANAGE = "tenants.manage"   # Full tenant management (billing, subscription)

    # ========================================
    # Store Management Permissions
    # ========================================
    STORES_VIEW = "stores.view"         # View store list and details
    STORES_CREATE = "stores.create"     # Create new stores
    STORES_EDIT = "stores.edit"         # Edit store details
    STORES_DELETE = "stores.delete"     # Delete/deactivate stores
    STORES_MANAGE_USERS = "stores.manage_users"  # Assign/remove users from stores

    # ========================================
    # Role & Permission Management
    # ========================================
    ROLES_VIEW = "roles.view"           # View roles and their permissions
    ROLES_CREATE = "roles.create"       # Create new roles
    ROLES_EDIT = "roles.edit"           # Edit role details and permissions
    ROLES_DELETE = "roles.delete"       # Delete roles
    PERMISSIONS_VIEW = "permissions.view"  # View available permissions

    # ========================================
    # Product Management Permissions
    # ========================================
    PRODUCTS_VIEW = "products.view"     # View products
    PRODUCTS_CREATE = "products.create" # Create new products
    PRODUCTS_EDIT = "products.edit"     # Edit product details
    PRODUCTS_DELETE = "products.delete" # Delete products
    PRODUCTS_MANAGE_PRICING = "products.manage_pricing"  # Manage product pricing
    PRODUCTS_MANAGE_INVENTORY = "products.manage_inventory"  # Manage stock levels

    # ========================================
    # Order Management Permissions
    # ========================================
    ORDERS_VIEW = "orders.view"         # View orders
    ORDERS_CREATE = "orders.create"     # Create new orders
    ORDERS_EDIT = "orders.edit"         # Edit orders
    ORDERS_CANCEL = "orders.cancel"     # Cancel orders
    ORDERS_REFUND = "orders.refund"     # Process refunds

    # ========================================
    # Invoice & Billing Permissions
    # ========================================
    INVOICES_VIEW = "invoices.view"     # View invoices
    INVOICES_CREATE = "invoices.create" # Create invoices
    INVOICES_EDIT = "invoices.edit"     # Edit invoices
    INVOICES_DELETE = "invoices.delete" # Delete invoices
    INVOICES_SEND = "invoices.send"     # Send invoices to customers

    # ========================================
    # Payment Permissions
    # ========================================
    PAYMENTS_VIEW = "payments.view"     # View payment records
    PAYMENTS_PROCESS = "payments.process"  # Process payments
    PAYMENTS_REFUND = "payments.refund" # Process payment refunds

    # ========================================
    # Report & Analytics Permissions
    # ========================================
    REPORTS_VIEW = "reports.view"       # View reports
    REPORTS_EXPORT = "reports.export"   # Export report data
    ANALYTICS_VIEW = "analytics.view"   # View analytics dashboards

    # ========================================
    # Settings & Configuration
    # ========================================
    SETTINGS_VIEW = "settings.view"     # View system settings
    SETTINGS_EDIT = "settings.edit"     # Edit system settings

    # ========================================
    # Subscription & Billing (Tenant-level)
    # ========================================
    SUBSCRIPTION_VIEW = "subscription.view"   # View subscription details
    SUBSCRIPTION_MANAGE = "subscription.manage"  # Manage subscription
    BILLING_VIEW = "billing.view"       # View billing history
    BILLING_MANAGE = "billing.manage"   # Manage billing settings

    # ========================================
    # Notification Permissions
    # ========================================
    NOTIFICATIONS_VIEW = "notifications.view"     # View notifications
    NOTIFICATIONS_MANAGE = "notifications.manage" # Manage notification settings


# All permissions as a list for iteration/seeding
ALL_PERMISSIONS = [
    # Users
    {"name": Permissions.USERS_VIEW, "resource": "users", "action": "view", "description": "View user list and user details"},
    {"name": Permissions.USERS_CREATE, "resource": "users", "action": "create", "description": "Invite or create new users in the tenant"},
    {"name": Permissions.USERS_EDIT, "resource": "users", "action": "edit", "description": "Edit user details and profile"},
    {"name": Permissions.USERS_DELETE, "resource": "users", "action": "delete", "description": "Deactivate or remove users from the tenant"},
    {"name": Permissions.USERS_MANAGE_ROLES, "resource": "users", "action": "manage_roles", "description": "Assign or revoke roles for users"},

    # Tenants
    {"name": Permissions.TENANTS_VIEW, "resource": "tenants", "action": "view", "description": "View tenant settings and information"},
    {"name": Permissions.TENANTS_EDIT, "resource": "tenants", "action": "edit", "description": "Edit tenant settings and information"},
    {"name": Permissions.TENANTS_MANAGE, "resource": "tenants", "action": "manage", "description": "Full tenant management including billing and subscription"},

    # Stores
    {"name": Permissions.STORES_VIEW, "resource": "stores", "action": "view", "description": "View store list and store details"},
    {"name": Permissions.STORES_CREATE, "resource": "stores", "action": "create", "description": "Create new stores"},
    {"name": Permissions.STORES_EDIT, "resource": "stores", "action": "edit", "description": "Edit store details and settings"},
    {"name": Permissions.STORES_DELETE, "resource": "stores", "action": "delete", "description": "Delete or deactivate stores"},
    {"name": Permissions.STORES_MANAGE_USERS, "resource": "stores", "action": "manage_users", "description": "Assign or remove users from stores"},

    # Roles
    {"name": Permissions.ROLES_VIEW, "resource": "roles", "action": "view", "description": "View roles and their assigned permissions"},
    {"name": Permissions.ROLES_CREATE, "resource": "roles", "action": "create", "description": "Create new custom roles"},
    {"name": Permissions.ROLES_EDIT, "resource": "roles", "action": "edit", "description": "Edit role details and permissions"},
    {"name": Permissions.ROLES_DELETE, "resource": "roles", "action": "delete", "description": "Delete custom roles"},
    {"name": Permissions.PERMISSIONS_VIEW, "resource": "permissions", "action": "view", "description": "View available permissions in the system"},

    # Products
    {"name": Permissions.PRODUCTS_VIEW, "resource": "products", "action": "view", "description": "View product catalog and product details"},
    {"name": Permissions.PRODUCTS_CREATE, "resource": "products", "action": "create", "description": "Create new products"},
    {"name": Permissions.PRODUCTS_EDIT, "resource": "products", "action": "edit", "description": "Edit product details"},
    {"name": Permissions.PRODUCTS_DELETE, "resource": "products", "action": "delete", "description": "Delete products from catalog"},
    {"name": Permissions.PRODUCTS_MANAGE_PRICING, "resource": "products", "action": "manage_pricing", "description": "Manage product pricing and discounts"},
    {"name": Permissions.PRODUCTS_MANAGE_INVENTORY, "resource": "products", "action": "manage_inventory", "description": "Manage product stock and inventory levels"},

    # Orders
    {"name": Permissions.ORDERS_VIEW, "resource": "orders", "action": "view", "description": "View order list and order details"},
    {"name": Permissions.ORDERS_CREATE, "resource": "orders", "action": "create", "description": "Create new orders"},
    {"name": Permissions.ORDERS_EDIT, "resource": "orders", "action": "edit", "description": "Edit order details"},
    {"name": Permissions.ORDERS_CANCEL, "resource": "orders", "action": "cancel", "description": "Cancel orders"},
    {"name": Permissions.ORDERS_REFUND, "resource": "orders", "action": "refund", "description": "Process order refunds"},

    # Invoices
    {"name": Permissions.INVOICES_VIEW, "resource": "invoices", "action": "view", "description": "View invoice list and details"},
    {"name": Permissions.INVOICES_CREATE, "resource": "invoices", "action": "create", "description": "Create new invoices"},
    {"name": Permissions.INVOICES_EDIT, "resource": "invoices", "action": "edit", "description": "Edit invoice details"},
    {"name": Permissions.INVOICES_DELETE, "resource": "invoices", "action": "delete", "description": "Delete draft invoices"},
    {"name": Permissions.INVOICES_SEND, "resource": "invoices", "action": "send", "description": "Send invoices to customers"},

    # Payments
    {"name": Permissions.PAYMENTS_VIEW, "resource": "payments", "action": "view", "description": "View payment records and history"},
    {"name": Permissions.PAYMENTS_PROCESS, "resource": "payments", "action": "process", "description": "Process customer payments"},
    {"name": Permissions.PAYMENTS_REFUND, "resource": "payments", "action": "refund", "description": "Process payment refunds"},

    # Reports
    {"name": Permissions.REPORTS_VIEW, "resource": "reports", "action": "view", "description": "View business reports"},
    {"name": Permissions.REPORTS_EXPORT, "resource": "reports", "action": "export", "description": "Export report data"},
    {"name": Permissions.ANALYTICS_VIEW, "resource": "analytics", "action": "view", "description": "View analytics dashboards"},

    # Settings
    {"name": Permissions.SETTINGS_VIEW, "resource": "settings", "action": "view", "description": "View system settings"},
    {"name": Permissions.SETTINGS_EDIT, "resource": "settings", "action": "edit", "description": "Edit system settings"},

    # Subscription & Billing
    {"name": Permissions.SUBSCRIPTION_VIEW, "resource": "subscription", "action": "view", "description": "View subscription plan and status"},
    {"name": Permissions.SUBSCRIPTION_MANAGE, "resource": "subscription", "action": "manage", "description": "Manage subscription plan changes"},
    {"name": Permissions.BILLING_VIEW, "resource": "billing", "action": "view", "description": "View billing history and invoices"},
    {"name": Permissions.BILLING_MANAGE, "resource": "billing", "action": "manage", "description": "Manage billing settings and payment methods"},

    # Notifications
    {"name": Permissions.NOTIFICATIONS_VIEW, "resource": "notifications", "action": "view", "description": "View notifications"},
    {"name": Permissions.NOTIFICATIONS_MANAGE, "resource": "notifications", "action": "manage", "description": "Manage notification preferences"},
]


# Default role definitions with their permissions
# These are created when a new tenant is bootstrapped
DEFAULT_ROLES = {
    "Owner": {
        "description": "Full access to all tenant resources. Cannot be deleted.",
        "is_system_role": True,
        "permissions": [p["name"] for p in ALL_PERMISSIONS],  # All permissions
    },
    "Admin": {
        "description": "Administrative access to manage users, stores, and settings.",
        "is_system_role": True,
        "permissions": [
            Permissions.USERS_VIEW,
            Permissions.USERS_CREATE,
            Permissions.USERS_EDIT,
            Permissions.USERS_DELETE,
            Permissions.USERS_MANAGE_ROLES,
            Permissions.STORES_VIEW,
            Permissions.STORES_CREATE,
            Permissions.STORES_EDIT,
            Permissions.STORES_DELETE,
            Permissions.STORES_MANAGE_USERS,
            Permissions.ROLES_VIEW,
            Permissions.ROLES_CREATE,
            Permissions.ROLES_EDIT,
            Permissions.ROLES_DELETE,
            Permissions.PERMISSIONS_VIEW,
            Permissions.TENANTS_VIEW,
            Permissions.TENANTS_EDIT,
            Permissions.SETTINGS_VIEW,
            Permissions.SETTINGS_EDIT,
            Permissions.REPORTS_VIEW,
            Permissions.REPORTS_EXPORT,
            Permissions.ANALYTICS_VIEW,
        ],
    },
    "Manager": {
        "description": "Store management access with user and product management.",
        "is_system_role": True,
        "permissions": [
            Permissions.USERS_VIEW,
            Permissions.STORES_VIEW,
            Permissions.STORES_EDIT,
            Permissions.STORES_MANAGE_USERS,
            Permissions.PRODUCTS_VIEW,
            Permissions.PRODUCTS_CREATE,
            Permissions.PRODUCTS_EDIT,
            Permissions.PRODUCTS_DELETE,
            Permissions.PRODUCTS_MANAGE_PRICING,
            Permissions.PRODUCTS_MANAGE_INVENTORY,
            Permissions.ORDERS_VIEW,
            Permissions.ORDERS_CREATE,
            Permissions.ORDERS_EDIT,
            Permissions.ORDERS_CANCEL,
            Permissions.INVOICES_VIEW,
            Permissions.INVOICES_CREATE,
            Permissions.INVOICES_EDIT,
            Permissions.INVOICES_SEND,
            Permissions.PAYMENTS_VIEW,
            Permissions.PAYMENTS_PROCESS,
            Permissions.REPORTS_VIEW,
        ],
    },
    "Cashier": {
        "description": "Point of sale operations - orders, payments, and basic product view.",
        "is_system_role": True,
        "permissions": [
            Permissions.PRODUCTS_VIEW,
            Permissions.ORDERS_VIEW,
            Permissions.ORDERS_CREATE,
            Permissions.INVOICES_VIEW,
            Permissions.INVOICES_CREATE,
            Permissions.PAYMENTS_VIEW,
            Permissions.PAYMENTS_PROCESS,
        ],
    },
    "Viewer": {
        "description": "Read-only access to view data without modification rights.",
        "is_system_role": True,
        "permissions": [
            Permissions.USERS_VIEW,
            Permissions.STORES_VIEW,
            Permissions.PRODUCTS_VIEW,
            Permissions.ORDERS_VIEW,
            Permissions.INVOICES_VIEW,
            Permissions.PAYMENTS_VIEW,
            Permissions.REPORTS_VIEW,
        ],
    },
}
