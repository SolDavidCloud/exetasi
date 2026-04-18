/**
 * OpenAPI paths for the Exetasi backend.
 * Regenerate with `pnpm codegen` (requires backend running or OPENAPI_URL).
 */

export interface components {
  schemas: {
    UserPublic: {
      id: string;
      username: string;
      bio: string;
      avatar_url: string | null;
      is_superuser: boolean;
      can_create_orgs: boolean;
    };
    AdminUserPublic: {
      id: string;
      username: string;
      bio: string;
      avatar_url: string | null;
      is_superuser: boolean;
      is_banned: boolean;
      ban_reason: string | null;
      can_create_orgs: boolean;
    };
    SetSuperuserRequest: {
      is_superuser: boolean;
    };
    SetCanCreateOrgsRequest: {
      allowed: boolean;
    };
    BanUserRequest: {
      reason?: string;
    };
    TransferOwnerRequest: {
      new_owner_username: string;
    };
    UserUpdate: {
      username?: string | null;
      bio?: string | null;
      avatar_url?: string | null;
    };
    OrganizationPublic: {
      id: string;
      name: string;
      slug: string;
      description: string;
      avatar_url: string | null;
      banner_url: string | null;
      primary_color: string | null;
      secondary_color: string | null;
      accent_color: string | null;
      is_personal: boolean;
      role: 'owner' | 'editor' | 'grader' | 'viewer';
    };
    OrganizationCreate: {
      name: string;
      slug?: string | null;
      description?: string;
    };
    OrganizationUpdate: {
      name?: string | null;
      slug?: string | null;
      description?: string | null;
      avatar_url?: string | null;
      banner_url?: string | null;
      primary_color?: string | null;
      secondary_color?: string | null;
      accent_color?: string | null;
    };
    ExamPublic: {
      id: string;
      org_id: string;
      name: string;
      is_archived: boolean;
      visibility: string;
    };
    ExamCreate: {
      name: string;
      public_description?: string;
      private_description?: string;
      visibility?: 'public' | 'restricted';
    };
    AuthProviders: {
      google: boolean;
      github: boolean;
      gitlab: boolean;
      dev: boolean;
    };
    AuditLogEntry: {
      id: string;
      created_at: string;
      actor_user_id: string | null;
      org_id: string | null;
      action: string;
      target_type: string | null;
      target_id: string | null;
      metadata: Record<string, unknown>;
    };
  };
  responses: never;
  parameters: never;
  requestBodies: never;
  headers: never;
  pathItems: never;
}

export interface paths {
  '/api/v1/health': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get: {
      parameters: {
        query?: never;
        header?: never;
        path?: never;
        cookie?: never;
      };
      responses: {
        200: {
          headers: Record<string, unknown>;
          content: {
            'application/json': {
              /** @enum {string} */
              status: 'ok';
            };
          };
        };
      };
    };
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/auth/providers': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get: {
      parameters: {
        query?: never;
        header?: never;
        path?: never;
        cookie?: never;
      };
      responses: {
        200: {
          headers: Record<string, unknown>;
          content: {
            'application/json': components['schemas']['AuthProviders'];
          };
        };
      };
    };
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/audit-log': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get: {
      parameters: {
        query?: {
          org_slug?: string | null;
          limit?: number | null;
        };
        header?: never;
        path?: never;
        cookie?: never;
      };
      responses: {
        200: {
          headers: Record<string, unknown>;
          content: {
            'application/json': {
              entries: Array<components['schemas']['AuditLogEntry']>;
            };
          };
        };
      };
    };
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/auth/dev/login': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    put?: never;
    post: {
      parameters: {
        query?: never;
        header?: never;
        path?: never;
        cookie?: never;
      };
      requestBody: {
        content: {
          'application/json': {
            username: string;
          };
        };
      };
      responses: {
        204: {
          headers: Record<string, unknown>;
          content?: never;
        };
        403: {
          headers: Record<string, unknown>;
          content: {
            'application/json': {
              detail: {
                code: 'banned';
                reason: string;
              };
            };
          };
        };
      };
    };
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/auth/logout': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    put?: never;
    post: {
      parameters: {
        query?: never;
        header?: never;
        path?: never;
        cookie?: never;
      };
      responses: {
        204: {
          headers: Record<string, unknown>;
          content?: never;
        };
      };
    };
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/users/me': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get: {
      parameters: {
        query?: never;
        header?: never;
        path?: never;
        cookie?: never;
      };
      responses: {
        200: {
          headers: Record<string, unknown>;
          content: {
            'application/json': components['schemas']['UserPublic'];
          };
        };
      };
    };
    put?: never;
    post?: never;
    delete: {
      parameters: {
        query?: never;
        header?: never;
        path?: never;
        cookie?: never;
      };
      responses: {
        204: {
          headers: Record<string, unknown>;
          content?: never;
        };
      };
    };
    options?: never;
    head?: never;
    patch: {
      parameters: {
        query?: never;
        header?: never;
        path?: never;
        cookie?: never;
      };
      requestBody: {
        content: {
          'application/json': components['schemas']['UserUpdate'];
        };
      };
      responses: {
        200: {
          headers: Record<string, unknown>;
          content: {
            'application/json': components['schemas']['UserPublic'];
          };
        };
      };
    };
    trace?: never;
  };
  '/api/v1/orgs': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get: {
      parameters: {
        query?: never;
        header?: never;
        path?: never;
        cookie?: never;
      };
      responses: {
        200: {
          headers: Record<string, unknown>;
          content: {
            'application/json': Array<components['schemas']['OrganizationPublic']>;
          };
        };
      };
    };
    put?: never;
    post: {
      parameters: {
        query?: never;
        header?: never;
        path?: never;
        cookie?: never;
      };
      requestBody: {
        content: {
          'application/json': components['schemas']['OrganizationCreate'];
        };
      };
      responses: {
        201: {
          headers: Record<string, unknown>;
          content: {
            'application/json': components['schemas']['OrganizationPublic'];
          };
        };
      };
    };
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/orgs/{org_slug}': {
    parameters: {
      query?: never;
      header?: never;
      path: {
        org_slug: string;
      };
      cookie?: never;
    };
    get: {
      parameters: {
        query?: never;
        header?: never;
        path: {
          org_slug: string;
        };
        cookie?: never;
      };
      responses: {
        200: {
          headers: Record<string, unknown>;
          content: {
            'application/json': components['schemas']['OrganizationPublic'];
          };
        };
      };
    };
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch: {
      parameters: {
        query?: never;
        header?: never;
        path: {
          org_slug: string;
        };
        cookie?: never;
      };
      requestBody: {
        content: {
          'application/json': components['schemas']['OrganizationUpdate'];
        };
      };
      responses: {
        200: {
          headers: Record<string, unknown>;
          content: {
            'application/json': components['schemas']['OrganizationPublic'];
          };
        };
      };
    };
    trace?: never;
  };
  '/api/v1/admin/users': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get: {
      parameters: {
        query?: {
          q?: string | null;
          limit?: number | null;
          offset?: number | null;
        };
        header?: never;
        path?: never;
        cookie?: never;
      };
      responses: {
        200: {
          headers: Record<string, unknown>;
          content: {
            'application/json': Array<components['schemas']['AdminUserPublic']>;
          };
        };
      };
    };
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/admin/users/{username}/superuser': {
    parameters: {
      query?: never;
      header?: never;
      path: { username: string };
      cookie?: never;
    };
    get?: never;
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch: {
      parameters: {
        query?: never;
        header?: never;
        path: { username: string };
        cookie?: never;
      };
      requestBody: {
        content: {
          'application/json': components['schemas']['SetSuperuserRequest'];
        };
      };
      responses: {
        200: {
          headers: Record<string, unknown>;
          content: {
            'application/json': components['schemas']['AdminUserPublic'];
          };
        };
      };
    };
    trace?: never;
  };
  '/api/v1/admin/users/{username}/can-create-orgs': {
    parameters: {
      query?: never;
      header?: never;
      path: { username: string };
      cookie?: never;
    };
    get?: never;
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch: {
      parameters: {
        query?: never;
        header?: never;
        path: { username: string };
        cookie?: never;
      };
      requestBody: {
        content: {
          'application/json': components['schemas']['SetCanCreateOrgsRequest'];
        };
      };
      responses: {
        200: {
          headers: Record<string, unknown>;
          content: {
            'application/json': components['schemas']['AdminUserPublic'];
          };
        };
      };
    };
    trace?: never;
  };
  '/api/v1/admin/users/{username}/ban': {
    parameters: {
      query?: never;
      header?: never;
      path: { username: string };
      cookie?: never;
    };
    get?: never;
    put?: never;
    post: {
      parameters: {
        query?: never;
        header?: never;
        path: { username: string };
        cookie?: never;
      };
      requestBody: {
        content: {
          'application/json': components['schemas']['BanUserRequest'];
        };
      };
      responses: {
        200: {
          headers: Record<string, unknown>;
          content: {
            'application/json': components['schemas']['AdminUserPublic'];
          };
        };
      };
    };
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/admin/users/{username}/unban': {
    parameters: {
      query?: never;
      header?: never;
      path: { username: string };
      cookie?: never;
    };
    get?: never;
    put?: never;
    post: {
      parameters: {
        query?: never;
        header?: never;
        path: { username: string };
        cookie?: never;
      };
      responses: {
        200: {
          headers: Record<string, unknown>;
          content: {
            'application/json': components['schemas']['AdminUserPublic'];
          };
        };
      };
    };
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/admin/orgs/{org_slug}/transfer-owner': {
    parameters: {
      query?: never;
      header?: never;
      path: { org_slug: string };
      cookie?: never;
    };
    get?: never;
    put?: never;
    post: {
      parameters: {
        query?: never;
        header?: never;
        path: { org_slug: string };
        cookie?: never;
      };
      requestBody: {
        content: {
          'application/json': components['schemas']['TransferOwnerRequest'];
        };
      };
      responses: {
        200: {
          headers: Record<string, unknown>;
          content: {
            'application/json': components['schemas']['OrganizationPublic'];
          };
        };
      };
    };
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/orgs/{org_slug}/exams': {
    parameters: {
      query?: never;
      header?: never;
      path: {
        org_slug: string;
      };
      cookie?: never;
    };
    get: {
      parameters: {
        query?: never;
        header?: never;
        path: {
          org_slug: string;
        };
        cookie?: never;
      };
      responses: {
        200: {
          headers: Record<string, unknown>;
          content: {
            'application/json': Array<components['schemas']['ExamPublic']>;
          };
        };
      };
    };
    put?: never;
    post: {
      parameters: {
        query?: never;
        header?: never;
        path: {
          org_slug: string;
        };
        cookie?: never;
      };
      requestBody: {
        content: {
          'application/json': components['schemas']['ExamCreate'];
        };
      };
      responses: {
        201: {
          headers: Record<string, unknown>;
          content: {
            'application/json': components['schemas']['ExamPublic'];
          };
        };
      };
    };
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
}

export type webhooks = Record<string, never>;

export type $defs = Record<string, never>;

export type operations = Record<string, never>;
