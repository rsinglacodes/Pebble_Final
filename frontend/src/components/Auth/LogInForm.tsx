import React, { useState, useRef } from 'react';
import { TextField } from './TextField.tsx';
import { PasswordField } from './PasswordField.tsx';
import { GoogleButton } from './GoogleButton.tsx';
import { authContent } from '../../content.ts';
import { logIn, LogInParams } from '../../lib/auth.ts';

interface LogInFormProps {
  onSuccess: (name: string) => void;
  onSwitchToSignUp: () => void;
  onGoogleSignIn: () => void;
  isGoogleLoading?: boolean;
  onTriggerShake: () => void;
  onHoverStart?: (type?: string) => void;
  onHoverEnd?: () => void;
}

export const LogInForm: React.FC<LogInFormProps> = ({
  onSuccess,
  onSwitchToSignUp,
  onGoogleSignIn,
  isGoogleLoading = false,
  onTriggerShake,
  onHoverStart,
  onHoverEnd,
}) => {
  const [formData, setFormData] = useState({
    email: '',
    password: '',
  });

  const [errors, setErrors] = useState<Record<string, string>>({});
  const [touched, setTouched] = useState<Record<string, boolean>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [genericError, setGenericError] = useState<string | null>(null);

  const emailRef = useRef<HTMLInputElement | null>(null);
  const passwordRef = useRef<HTMLInputElement | null>(null);

  const validateField = (field: keyof typeof formData, value: string): string | undefined => {
    switch (field) {
      case 'email':
        if (!value.trim() || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value.trim())) {
          return authContent.errors.emailInvalid;
        }
        break;
      case 'password':
        if (!value) {
          return authContent.errors.loginPasswordRequired;
        }
        break;
    }
    return undefined;
  };

  const handleChange = (field: keyof typeof formData) => (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    setFormData((prev) => ({ ...prev, [field]: val }));
    setGenericError(null);

    if (touched[field]) {
      const err = validateField(field, val);
      setErrors((prev) => ({ ...prev, [field]: err || '' }));
    }
  };

  const handleBlur = (field: keyof typeof formData) => () => {
    setTouched((prev) => ({ ...prev, [field]: true }));
    const err = validateField(field, formData[field]);
    setErrors((prev) => ({ ...prev, [field]: err || '' }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setGenericError(null);

    const newErrors: Record<string, string> = {};
    (['email', 'password'] as const).forEach((f) => {
      const err = validateField(f, formData[f]);
      if (err) newErrors[f] = err;
    });

    setTouched({
      email: true,
      password: true,
    });
    setErrors(newErrors);

    if (Object.keys(newErrors).length > 0) {
      onTriggerShake();
      if (newErrors.email) {
        emailRef.current?.focus();
      } else if (newErrors.password) {
        passwordRef.current?.focus();
      }
      return;
    }

    setIsSubmitting(true);
    try {
      const params: LogInParams = {
        email: formData.email,
        password: formData.password,
      };
      const res = await logIn(params);
      onSuccess(res.user.name);
    } catch (err) {
        setGenericError(err instanceof Error && err.message ? err.message : authContent.errors.genericFailure);
      onTriggerShake();
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="w-full flex flex-col gap-3" noValidate>
      {/* 1. Email Address */}
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

      {/* 2. Password with Forgot Password link below */}
      <div className="flex flex-col gap-1.5">
        <PasswordField
          ref={passwordRef}
          placeholder={authContent.fields.password.placeholder}
          aria-label={authContent.fields.password.label}
          autoComplete="current-password"
          value={formData.password}
          onChange={handleChange('password')}
          onBlur={handleBlur('password')}
          error={touched.password ? errors.password : undefined}
          disabled={isSubmitting || isGoogleLoading}
          onHoverStart={onHoverStart}
          onHoverEnd={onHoverEnd}
        />

        <div className="flex justify-end pr-1">
          <a
            href="#"
            onClick={(e) => e.preventDefault()}
            onMouseEnter={() => onHoverStart?.('button')}
            onMouseLeave={onHoverEnd}
            className="text-[12px] text-[#8A8A90] hover:text-[#111113] transition-colors focus:outline-none"
          >
            {authContent.forgotPassword}
          </a>
        </div>
      </div>

      {/* Generic Error Notice */}
      {genericError && (
        <p className="text-[12px] font-medium text-[#D9485F] text-center" aria-live="polite">
          {genericError}
        </p>
      )}

      {/* 3. Primary Submit Button: Solid near-black #111113 */}
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
          <span>{authContent.submit.login}</span>
        )}
      </button>

      {/* 4. Divider */}
      <div className="flex items-center gap-3 my-0.5 select-none">
        <div className="flex-1 h-px bg-[#E2E2E7]" />
        <span className="text-[12px] text-[#8A8A90] font-normal">{authContent.divider.login}</span>
        <div className="flex-1 h-px bg-[#E2E2E7]" />
      </div>

      {/* 5. Continue with Google */}
      <GoogleButton
        onClick={onGoogleSignIn}
        isLoading={isGoogleLoading}
        disabled={isSubmitting}
        onHoverStart={onHoverStart}
        onHoverEnd={onHoverEnd}
      />

      {/* 6. Footer Text */}
      <div className="flex flex-col items-center justify-center mt-2 select-none">
        <p className="text-[12px] sm:text-[13px] text-[#8A8A90]">
          {authContent.footer.login.switchPrompt}{' '}
          <button
            type="button"
            onClick={onSwitchToSignUp}
            onMouseEnter={() => onHoverStart?.('button')}
            onMouseLeave={onHoverEnd}
            className="text-[#111113] font-semibold hover:underline transition-colors focus:outline-none"
          >
            {authContent.footer.login.switchAction}
          </button>
        </p>
      </div>
    </form>
  );
};
