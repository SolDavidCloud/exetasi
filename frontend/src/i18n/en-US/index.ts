export default {
  error: {
    notFound: 'Nothing here…',
    goHome: 'Go home',
  },
  app: {
    title: 'Exetasi',
  },
  layout: {
    menu: 'Menu',
    drawerAria: 'Navigation drawer',
  },
  auth: {
    loginTitle: 'Sign in',
    loginLead: 'Use a configured OAuth provider or local development sign-in.',
    loginNav: 'Sign in',
    provider: {
      google: 'Continue with Google',
      github: 'Continue with GitHub',
      gitlab: 'Continue with GitLab',
    },
    devLoginHint: 'Local development only (requires ENABLE_DEV_AUTH on the API).',
    username: 'Username',
    devLogin: 'Sign in (development)',
    devLoginFailed: 'Development sign-in failed.',
    logout: 'Sign out',
    loggedOut: 'Signed out.',
  },
  orgs: {
    title: 'Organizations',
    empty: 'No organizations yet.',
    createTitle: 'Create a team organization',
    name: 'Name',
    create: 'Create',
    createFailed: 'Could not create organization.',
    viewExams: 'Exams',
    examsFor: 'Exams in {slug}',
  },
  profile: {
    title: 'Profile',
    username: 'Username',
    noBio: 'No bio yet.',
  },
  home: {
    title: 'Exetasi',
    lead: 'Quiz and exam platform.',
    pingBackend: 'Check API health',
    backendOk: 'API status: {status}',
    backendError: 'Could not reach the API.',
    unknown: 'Unknown',
  },
};
