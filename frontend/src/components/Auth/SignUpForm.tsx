import React, { useState, useRef } from 'react';
import { TextField } from './TextField.tsx';
import { PasswordField } from './PasswordField.tsx';
import { GoogleButton } from './GoogleButton.tsx';
import { authContent } from '../../content.ts';
import { signUp, SignUpParams } from '../../lib/auth.ts';
import { ApiError } from '../../lib/api.ts';

interface SignUpFormProps {
  onSuccess: (name: string) => void;
  onSwitchToLogIn: () => void;
  onGoogleSignIn: () => void;
  isGoogleLoading?: boolean;
  onTriggerShake: () => void;
  onHoverStart?: (type?: string) => void;
  onHoverEnd?: () => void;
}

export const SignUpForm: React.FC<SignUpFormProps> = ({
  onSuccess,
  onSwitchToLogIn,
  onGoogleSignIn,
  isGoogleLoading = false,
  onTriggerShake,
  onHoverStart,
  onHoverEnd,
}) => {
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    password: '',
    confirmPassword: '',
  });

  const [errors, setErrors] = useState<Record<string, string>>({});
  const [touched, setTouched] = useState<Record<string, boolean>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [serverError, setServerError] = useState<{ message: string; is409?: boolean } | null>(null);

  const nameRef = useRef<HTMLInputElement | null>(null);
  const emailRef = useRef<HTMLInputElement | null>(null);
  const passwordRef = useRef<HTMLInputElement | null>(null);
  const confirmPasswordRef = useRef<HTMLInputElement | null>(null);

  const validateField = (field: keyof typeof formData, value: string): string | undefined => {
    switch (field) {
      case 'name':
        if (!value.trim() || value.trim().length < 2) {
          return authContent.errors.nameRequired;
        }
        break;
      case 'email':
        if (!value.trim() || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value.trim())) {
          return authContent.errors.emailInvalid;
        }
        break;
      case 'password':
        if (!value || value.length < 8) {
          return authContent.errors.passwordLength;
        }
        break;
      case 'confirmPassword':
        if (!value || value !== formData.password) {
          return authContent.errors.passwordMismatch;
        }
        break;
    }
    return undefined;
  };

  const handleChange = (field: keyof typeof formData) => (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    setFormData((prev) => ({ ...prev, [field]: val }));
    setServerError(null);

    if (field === 'email' && errors.email === "You are already registered with this email. Please log in.") {
      setErrors((prev) => ({ ...prev, email: '' }));
    }

    if (touched[field]) {
      const err = validateField(field, val);
      setErrors((prev) => ({ ...prev, [field]: err || '' }));
    }

    if (field === 'password' && touched.confirmPassword) {
      if (formData.confirmPassword && val !== formData.confirmPassword) {
        setErrors((prev) => ({ ...prev, confirmPassword: authContent.errors.passwordMismatch }));
      } else {
        setErrors((prev) => ({ ...prev, confirmPassword: '' }));
      }
    }
  };

  const handleBlur = (field: keyof typeof formData) => () => {
    setTouched((prev) => ({ ...prev, [field]: true }));
    const err = validateField(field, formData[field]);
    setErrors((prev) => ({ ...prev, [field]: err || '' }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setServerError(null);

    const newErrors: Record<string, string> = {};
    (['name', 'email', 'password', 'confirmPassword'] as const).forEach((f) => {
      const err = validateField(f, formData[f]);
      if (err) newErrors[f] = err;
    });

    setTouched({
      name: true,
      email: true,
      password: true,
      confirmPassword: true,
    });
    setErrors(newErrors);

    if (Object.keys(newErrors).length > 0) {
      onTriggerShake();
      if (newErrors.name) {
        nameRef.current?.focus();
      } else if (newErrors.email) {
        emailRef.current?.focus();
      } else if (newErrors.password) {
        passwordRef.current?.focus();
      } else if (newErrors.confirmPassword) {
        confirmPasswordRef.current?.focus();
      }
      return;
    }

    setIsSubmitting(true);
    try {
      const params: SignUpParams = {
        name: formData.name,
        email: formData.email,
        password: formData.password,
      };
      const res = await signUp(params);
      onSuccess(res.user.name);
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        const msg = "You are already registered with this email. Please log in.";
        setErrors((prev) => ({ ...prev, email: msg }));
        setTouched((prev) => ({ ...prev, email: true }));
        setServerError({ message: msg, is409: true });
      } else {
        const msg = err instanceof Error && err.message ? err.message : authContent.errors.genericFailure;
        setServerError({ message: msg, is409: false });
      }
      onTriggerShake();
    } finally {
      setIsSubmitting(false);
    }
  };

  const isMatched =
    formData.confirmPassword.length > 0 &&
    formData.confirmPassword === formData.password;

  return (
    <form onSubmit={handleSubmit} className="w-full flex flex-col gap-3" noValidate>
      {/* Red Error Banner */}
      {serverError && (
        <div
          role="alert"
          className="w-full rounded-[12px] bg-[#D9485F]/10 border border-[#D9485F]/25 px-3.5 py-2.5 text-[13px] text-[#D9485F] flex items-center justify-between gap-2"
        >
          <div className="flex-1 leading-snug">
            <span>{serverError.message}</span>
            {serverError.is409 && (
              <button
                type="button"
                onClick={onSwitchToLogIn}
                className="ml-1.5 underline font-semibold text-[#D9485F] hover:text-[#B82D44] cursor-pointer inline-flex items-center"
              >
                Log in
              </button>
            )}
          </div>
        </div>
      )}
      {/* 4 Fields with 12px gap */}
      <TextField
        ref={nameRef}
        placeholder={authContent.fields.name.placeholder}
        aria-label={authContent.fields.name.label}
        autoComplete="name"
        value={formData.name}
        onChange={handleChange('name')}
        onBlur={handleBlur('name')}
        error={touched.name ? errors.name : undefined}
        disabled={isSubmitting || isGoogleLoading}
        onHoverStart={onHoverStart}
        onHoverEnd={onHoverEnd}
      />

      <TextField
        ref={emailRef}
        type="email"
        placeholder={authContent.fields.email.placeholder}
        aria-label={authContent.fields.email.label}
        autoComplete="email"
        value={formData.email}
        onChange={handleChange('email')}
        onBlur={handleBlur('email')}
        error={touched.email ? errors.email : undefined}
        disabled={isSubmitting || isGoogleLoading}
        onHoverStart={onHoverStart}
        onHoverEnd={onHoverEnd}
      />

      <PasswordField
        ref={passwordRef}
        placeholder={authContent.fields.password.placeholder}
        aria-label={authContent.fields.password.label}
        autoComplete="new-password"
        value={formData.password}
        onChange={handleChange('password')}
        onBlur={handleBlur('password')}
        error={touched.password ? errors.password : undefined}
        showStrength={true}
        disabled={isSubmitting || isGoogleLoading}
        onHoverStart={onHoverStart}
        onHoverEnd={onHoverEnd}
      />

      <PasswordField
        ref={confirmPasswordRef}
        placeholder={authContent.fields.confirmPassword.placeholder}
        aria-label={authContent.fields.confirmPassword.label}
        autoComplete="new-password"
        value={formData.confirmPassword}
        onChange={handleChange('confirmPassword')}
        onBlur={handleBlur('confirmPassword')}
        error={touched.confirmPassword ? errors.confirmPassword : undefined}
        showMatchCheck={true}
        isMatched={isMatched}
        disabled={isSubmitting || isGoogleLoading}
        onHoverStart={onHoverStart}
        onHoverEnd={onHoverEnd}
      />

      {/* Generic Error Notice */}
      {/* Primary Submit Button: Solid near-black #111113 */}
      <button
        type="submit"
        disabled={isSubmitting || isGoogleLoading}
        onMouseEnter={() => onHoverStart?.('button')}
        onMouseLeave={onHoverEnd}
        className="w-full h-[48px] rounded-[12px] bg-[#111113] hover:bg-[#222226] text-white text-[15px] font-semibold flex items-center justify-center transition-all duration-200 shadow-sm hover:shadow-md hover:-translate-y-0.5 active:translate-y-0 disabled:opacity-60 disabled:pointer-events-none cursor-pointer focus:outline-none focus:ring-2 focus:ring-[#111113]/30"
      >
        {isSubmitting ? (
          <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
        ) : (
          <span>{authContent.submit.signup}</span>
        )}
      </button>

      {/* Hairline Divider */}
      <div className="flex items-center gap-3 my-0.5 select-none">
        <div className="flex-1 h-px bg-[#E2E2E7]" />
        <span className="text-[12px] text-[#8A8A90] font-normal">{authContent.divider.signup}</span>
        <div className="flex-1 h-px bg-[#E2E2E7]" />
      </div>

      {/* Continue with Google */}
      <GoogleButton
        onClick={onGoogleSignIn}
        isLoading={isGoogleLoading}
        disabled={isSubmitting}
        onHoverStart={onHoverStart}
        onHoverEnd={onHoverEnd}
      />

      {/* Small Muted Legal Text (12px) */}
      <div className="flex flex-col items-center gap-1.5 mt-0.5 text-center select-none">
        <p className="text-[11px] sm:text-[12px] text-[#8A8A90] leading-tight">
          By signing up, you agree to the{' '}
          <a
            href="#"
            onClick={(e) => e.preventDefault()}
            className="text-[#111113] font-medium hover:underline"
          >
            {authContent.footer.signup.termsLinkText}
          </a>{' '}
          and{' '}
          <a
            href="#"
            onClick={(e) => e.preventDefault()}
            className="text-[#111113] font-medium hover:underline"
          >
            {authContent.footer.signup.privacyLinkText}
          </a>
          .
        </p>

        <p className="text-[12px] sm:text-[13px] text-[#8A8A90]">
          {authContent.footer.signup.switchPrompt}{' '}
          <button
            type="button"
            onClick={onSwitchToLogIn}
            onMouseEnter={() => onHoverStart?.('button')}
            onMouseLeave={onHoverEnd}
            className="text-[#111113] font-semibold hover:underline transition-colors focus:outline-none"
          >
            {authContent.footer.signup.switchAction}
          </button>
        </p>
      </div>
    </form>
  );
};
