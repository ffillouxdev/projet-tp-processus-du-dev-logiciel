import type { Component } from 'vue'

export type InputSize = 'sm' | 'md' | 'lg'
export type InputVariant = 'default' | 'primary' | 'secondary' | 'ghost' | 'danger'
export type CheckboxSize = 'sm' | 'md' | 'lg'
export type CheckboxVariant = 'primary' | 'secondary' | 'ghost' | 'danger'

export interface UIInputProps {
  size?: InputSize
  variant?: InputVariant
  type?: string
  id?: string
  name?: string
  label?: string
  placeholder?: string
  hint?: string
  error?: boolean | string
  disabled?: boolean
  readonly?: boolean
  required?: boolean
  iconLeft?: Component | object | string
  iconRight?: Component | object | string
  iconPosition?: 'left' | 'right'
}

export interface UITextAreaProps {
  size?: InputSize
  variant?: InputVariant
  id?: string
  name?: string
  label?: string
  placeholder?: string
  hint?: string
  error?: boolean | string
  disabled?: boolean
  readonly?: boolean
  required?: boolean
  rows?: number | string
  resize?: 'none' | 'vertical' | 'horizontal' | 'both'
  maxlength?: number
  showCount?: boolean
}

export interface UICheckboxProps {
  size?: CheckboxSize
  variant?: CheckboxVariant
  id?: string
  name?: string
  label?: string
  hint?: string
  disabled?: boolean
  required?: boolean
  indeterminate?: boolean
  value?: unknown
  error?: boolean | string
}
