/**
 * Content configuration for the pebble landing experience.
 * All user-facing strings and data are kept in this file for easy replacement.
 */

export interface NavLinkItem {
  id: string;
  label: string;
  active?: boolean;
}

export interface CarouselSlide {
  id: string;
  caption: string;
  type: 'bars' | 'gradient' | 'gauge' | 'snack';
  title?: string;
  subtitle?: string;
  value?: string | number;
}

export const siteContent = {
  brand: {
    name: 'pebble',
    tagline: 'Animated explanations for every line of code',
  },
  navigation: {
    links: [
      { id: 'explore', label: 'Explore', active: true },
      { id: 'features', label: 'Features', active: false },
      { id: 'about', label: 'About Us', active: false },
    ] as NavLinkItem[],
    cta: 'Start Learning',
  },
  hero: {
    headline: {
      line1: "Stuck?",
      line2: "Visualize your code.",
      line3: "Work smarter.",
    },
    subtitle: "From confusing algorithms to animated explanations. Learn the logic, explore your code, and make every problem click with pebble.",
    cta: "Start Learning",
  },
  carousel: {
    slides: [
      {
        id: 'eye-contact',
        caption: 'Eye contact',
        type: 'bars',
        title: 'Gaze analysis',
      },
      {
        id: 'mood-swings',
        caption: 'Mood swings',
        type: 'gradient',
        title: 'Emotion matrix',
      },
      {
        id: 'focus-level',
        caption: 'Focus level',
        type: 'gauge',
        title: 'Attention tracking',
      },
      {
        id: 'snack-time',
        caption: 'Snack time',
        type: 'snack',
        title: 'Battery recharge',
      },
    ] as CarouselSlide[],
    slideDurationMs: 4000,
  },
};

export interface ThemeColors {
  gradientStart: string;
  gradientMid: string;
  gradientEnd: string;
  gradientCss: string;
  rimColors: [string, string, string];
  ctaBg: string;
  ctaText: string;
  cursorRing: string;
  cursorFill: string;
  cardAccent: string;
}

export const defaultColors: ThemeColors = {
  gradientStart: '#B33CF0',
  gradientMid: '#6C5CFF',
  gradientEnd: '#3CC8FF',
  gradientCss: 'linear-gradient(135deg, #B33CF0 0%, #6C5CFF 50%, #3CC8FF 100%)',
  rimColors: ['#B33CF0', '#6C5CFF', '#3CC8FF'],
  ctaBg: '#111113',
  ctaText: '#FFFFFF',
  cursorRing: 'rgba(108, 92, 255, 0.75)',
  cursorFill: 'rgba(108, 92, 255, 0.12)',
  cardAccent: '#6C5CFF',
};

export const featuresContent = {
  sectionIndex: '01-04',
  headline: {
    line1: 'See your code',
    line2: 'come alive',
  },
  uiCards: {
    visualize: {
      title: 'Visualize',
      subtext1: 'Watch every step run.',
      subtext2: 'Pause, rewind, replay.',
    },
    leetcode: {
      title: 'LeetCode problem',
      subtext: 'Paste any problem, see it solved.',
      problems: [
        { id: 1, name: '1. Two Sum', tag: 'Easy' },
        { id: 3, name: '3. Longest Substring', tag: 'Medium' },
      ],
    },
    complexity: {
      label: 'Time complexity',
      value: 'O(n log n)',
      badge: '+12% faster',
    },
  },
  tiles: {
    video: { chip: 'Walkthrough' },
    twoPointers: { chip: 'Two pointers' },
    algorithms: { chip: 'Algorithms' },
    yourCode: { chip: 'Your code' },
    sortingBars: { chip: 'Step by step' },
  },
  fragments: ['O(n)', 'left -> right', '{ your code }'],
};

export interface FooterLinkItem {
  label: string;
  href: string;
  isAnchor?: boolean;
  icon?: string;
}

export interface FooterColumn {
  title: string;
  links: FooterLinkItem[];
}

export const footerContent = {
  brand: {
    name: 'pebble',
    tagline: 'Watch algorithms think,\none step at a time.',
    cta: 'Start Learning ↗',
  },
  newsletter: {
    label: 'Stay updated',
    placeholder: 'Enter your email for updates...',
    buttonText: 'Join',
    successMessage: "You're on the list!",
  },
  columns: [
    {
      title: 'Explore',
      links: [
        { label: 'Explore', href: '#world', isAnchor: true },
        { label: 'Features', href: '#features', isAnchor: true },
        { label: 'About Us', href: '#hi', isAnchor: true },
      ],
    },
    {
      title: 'Learn',
      links: [
        { label: 'Two Pointers', href: '#', isAnchor: false },
        { label: 'Binary Search', href: '#', isAnchor: false },
        { label: 'Tree Traversal', href: '#', isAnchor: false },
        { label: 'Dynamic Programming', href: '#', isAnchor: false },
      ],
    },
    {
      title: 'Connect',
      links: [
        { label: 'GitHub', href: 'https://github.com', icon: 'github' },
        { label: 'X (Twitter)', href: 'https://twitter.com', icon: 'x' },
        { label: 'LinkedIn', href: 'https://linkedin.com', icon: 'linkedin' },
        { label: 'Email', href: 'mailto:hello@pebble.dev', icon: 'mail' },
      ],
    },
  ] as FooterColumn[],
  bottom: {
    copyright: `© ${new Date().getFullYear()} pebble. All rights reserved.`,
    legal: [
      { label: 'Privacy Policy', href: '#' },
      { label: 'Terms of Service', href: '#' },
    ],
  },
  wordmark: 'pebble',
};

export const authContent = {
  brand: {
    name: 'pebble',
  },
  tabs: {
    signup: 'Sign up',
    login: 'Log in',
  },
  titles: {
    signup: {
      title: 'Create your account',
      subtitle: 'Join pebble and watch your code come alive.',
    },
    login: {
      title: 'Welcome back',
      subtitle: 'Log in to pick up where you left off.',
    },
  },
  fields: {
    name: {
      label: 'Full name',
      placeholder: 'Full name',
    },
    email: {
      label: 'Email address',
      placeholder: 'Email address',
    },
    password: {
      label: 'Password',
      placeholder: 'Password',
      hint: 'At least 8 characters',
    },
    confirmPassword: {
      label: 'Confirm password',
      placeholder: 'Confirm password',
    },
  },
  submit: {
    signup: 'Sign up',
    login: 'Log in',
  },
  divider: {
    signup: 'Or sign up with',
    login: 'Or log in with',
  },
  google: {
    buttonText: 'Continue with Google',
  },
  footer: {
    signup: {
      termsNotice: 'By signing up, you agree to the Terms of Service and Privacy Policy.',
      termsLinkText: 'Terms of Service',
      privacyLinkText: 'Privacy Policy',
      switchPrompt: 'Already have an account?',
      switchAction: 'Log in',
    },
    login: {
      switchPrompt: "Don't have an account?",
      switchAction: 'Sign up',
    },
  },
  errors: {
    nameRequired: 'Full name must be at least 2 characters.',
    emailInvalid: 'Please enter a valid email address.',
    passwordLength: 'Password must be at least 8 characters.',
    passwordMismatch: "Passwords don't match",
    loginPasswordRequired: 'Password is required.',
    genericFailure: 'Something went wrong. Please try again.',
  },
  success: {
    signupTitle: "You're in, {name}!",
    loginTitle: 'Welcome back!',
    subtitle: 'Taking you to pebble...',
    continueButton: 'Continue',
  },
  forgotPassword: 'Forgot password?',
  showcase: {
    slides: [
      {
        quote: "Watch every step of your algorithm run, one move at a time.",
        label: "Visualize",
      },
      {
        quote: "Paste a LeetCode problem and see the two pointers move.",
        label: "Practice",
      },
      {
        quote: "Understand your own code, not just the answer.",
        label: "Learn",
      },
    ],
    durationMs: 5000,
  },
};
