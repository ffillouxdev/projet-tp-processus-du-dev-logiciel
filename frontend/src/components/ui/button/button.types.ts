import type { Component, InjectionKey, Ref } from 'vue'

export type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger'
export type ButtonSize = 'sm' | 'md' | 'lg'
export type ButtonType = 'button' | 'submit' | 'reset'
export type IconPosition = 'left' | 'right'
export type ButtonGroupOrientation = 'horizontal' | 'vertical'

export interface UIButtonProps {
  variant?: ButtonVariant
  size?: ButtonSize
  type?: ButtonType
  disabled?: boolean
  loading?: boolean
  iconOnly?: boolean
  iconPosition?: IconPosition
  icon?: Component | object | string
  iconLeft?: Component | object | string
  iconRight?: Component | object | string
  onClick?: (event: MouseEvent) => unknown | Promise<unknown>
  action?: (event: MouseEvent) => unknown | Promise<unknown>
}

export interface ButtonGroupContext {
  size: Ref<ButtonSize | undefined>
  variant: Ref<ButtonVariant | undefined>
  disabled: Ref<boolean | undefined>
  orientation: Ref<ButtonGroupOrientation>
}

export const buttonGroupKey: InjectionKey<ButtonGroupContext> = Symbol('buttonGroup')

export interface UIButtonGroupProps {
  size?: ButtonSize
  variant?: ButtonVariant
  disabled?: boolean
  orientation?: ButtonGroupOrientation
  divided?: boolean
  attached?: boolean
  ariaLabel?: string
  fullWidth?: boolean
}
