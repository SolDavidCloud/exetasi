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
      is_personal: boolean;
    };
    OrganizationCreate: {
      name: string;
      slug?: string | null;
      description?: string;
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
