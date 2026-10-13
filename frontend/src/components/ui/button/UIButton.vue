<script setup lang="ts">
import { computed, inject, ref, useSlots } from 'vue'
import {
  buttonGroupKey,
  type ButtonSize,
  type ButtonType,
  type ButtonVariant,
  type IconPosition,
  type UIButtonProps,
} from './button.types'

export type { ButtonSize, ButtonType, ButtonVariant, IconPosition, UIButtonProps }

const props = withDefaults(defineProps<UIButtonProps>(), {
  variant: undefined,
  size: undefined,
  type: 'button',
  disabled: false,
  loading: false,
  iconOnly: false,
  iconPosition: 'left',
  icon: undefined,
  iconLeft: undefined,
  iconRight: undefined,
  onClick: undefined,
  action: undefined,
})

const slots = useSlots()
const buttonGroup = inject(buttonGroupKey, null)
const internalLoading = ref(false)

const actualSize = computed<ButtonSize>(() => props.size ?? buttonGroup?.size.value ?? 'md')
const actualVariant = computed<ButtonVariant>(() => props.variant ?? buttonGroup?.variant.value ?? 'primary')

const isWaiting = computed(() => props.loading || internalLoading.value)
const isDisabled = computed(() => props.disabled || (buttonGroup?.disabled.value ?? false) || isWaiting.value)

const isIconOnly = computed(() => {
  if (props.iconOnly) return true
  const hasIcon =
    Boolean(props.icon) ||
    Boolean(props.iconLeft) ||
    Boolean(props.iconRight) ||
    Boolean(slots.icon) ||
    Boolean(slots['icon-left']) ||
    Boolean(slots.leading) ||
    Boolean(slots['icon-right']) ||
    Boolean(slots.trailing)
  return hasIcon && !slots.default
})

const hasLeftIcon = computed(() => {
  if (isIconOnly.value) return false
  return (
    Boolean(slots['icon-left']) ||
    Boolean(slots.leading) ||
    Boolean(props.iconLeft) ||
    (props.iconPosition === 'left' && (Boolean(props.icon) || Boolean(slots.icon)))
  )
})

const leftIconComponent = computed(() => {
  return props.iconLeft ?? (props.iconPosition === 'left' ? props.icon : undefined)
})

const hasRightIcon = computed(() => {
  if (isIconOnly.value) return false
  return (
    Boolean(slots['icon-right']) ||
    Boolean(slots.trailing) ||
    Boolean(props.iconRight) ||
    (props.iconPosition === 'right' && (Boolean(props.icon) || Boolean(slots.icon)))
  )
})

const rightIconComponent = computed(() => {
  return props.iconRight ?? (props.iconPosition === 'right' ? props.icon : undefined)
})

const standaloneIconComponent = computed(() => {
  return props.icon ?? props.iconLeft ?? props.iconRight
})

const showRightSpinner = computed(() => {
  return isWaiting.value && !isIconOnly.value && props.iconPosition === 'right' && !hasLeftIcon.value
})

const showLeftSpinner = computed(() => {
  return isWaiting.value && !isIconOnly.value && !showRightSpinner.value
})

const sizeClasses = computed(() => {
  if (isIconOnly.value) {
    switch (actualSize.value) {
      case 'sm':
        return 'h-8 w-8 p-0 rounded-md'
      case 'lg':
        return 'h-12 w-12 p-0 rounded-lg'
      case 'md':
      default:
        return 'h-10 w-10 p-0 rounded-md'
    }
  }

  switch (actualSize.value) {
    case 'sm':
      return 'h-8 px-3 text-xs gap-1.5 rounded-md'
    case 'lg':
      return 'h-12 px-6 text-base gap-2.5 rounded-lg'
    case 'md':
    default:
      return 'h-10 px-4 text-sm gap-2 rounded-md'
  }
})

const iconClasses = computed(() => {
  switch (actualSize.value) {
    case 'sm':
      return 'w-3.5 h-3.5 shrink-0'
    case 'lg':
      return 'w-5 h-5 shrink-0'
    case 'md':
    default:
      return 'w-4 h-4 shrink-0'
  }
})

const variantClasses = computed(() => {
  switch (actualVariant.value) {
    case 'secondary':
      return 'bg-secondary text-secondary-foreground hover:bg-secondary-hover active:bg-secondary-active focus-visible:ring-secondary'
    case 'ghost':
      return 'bg-ghost text-ghost-foreground hover:bg-ghost-hover active:bg-ghost-active focus-visible:ring-ghost'
    case 'danger':
      return 'bg-danger text-danger-foreground hover:bg-danger-hover active:bg-danger-active focus-visible:ring-danger'
    case 'primary':
    default:
      return 'bg-primary text-primary-foreground hover:bg-primary-hover active:bg-primary-active focus-visible:ring-primary'
  }
})

const baseClasses =
  'inline-flex items-center justify-center font-medium transition-colors duration-150 select-none cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed disabled:pointer-events-none'

const buttonClasses = computed(() => [
  baseClasses,
  sizeClasses.value,
  variantClasses.value,
])

async function handleClick(event: MouseEvent) {
  if (isDisabled.value) {
    event.preventDefault()
    event.stopPropagation()
    return
  }

  const handler = props.action ?? props.onClick
  if (handler) {
    const result = handler(event)
    if (result && typeof (result as Promise<unknown>).then === 'function') {
      internalLoading.value = true
      try {
        await result
      } finally {
        internalLoading.value = false
      }
    }
  }
}
</script>

<template>
  <button
    :type="type"
    :disabled="isDisabled"
    :aria-busy="isWaiting"
    :aria-disabled="isDisabled"
    :class="buttonClasses"
    @click="handleClick"
  >
    <!-- ICON ONLY BUTTON -->
    <template v-if="isIconOnly">
      <slot v-if="isWaiting" name="loading">
        <svg
          :class="iconClasses"
          class="animate-spin"
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
          aria-hidden="true"
        >
          <circle
            class="opacity-25"
            cx="12"
            cy="12"
            r="10"
            stroke="currentColor"
            stroke-width="4"
          />
          <path
            class="opacity-75"
            fill="currentColor"
            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
          />
        </svg>
      </slot>
      <slot v-else-if="$slots.icon" name="icon" />
      <slot v-else-if="$slots.default" />
      <slot v-else-if="$slots['icon-left']" name="icon-left" />
      <slot v-else-if="$slots.leading" name="leading" />
      <slot v-else-if="$slots['icon-right']" name="icon-right" />
      <slot v-else-if="$slots.trailing" name="trailing" />
      <component
        :is="standaloneIconComponent"
        v-else-if="standaloneIconComponent"
        :class="iconClasses"
        aria-hidden="true"
      />
    </template>

    <!-- STANDARD BUTTON (TEXT, OPTIONAL ICONS) -->
    <template v-else>
      <!-- Left Spinner (when waiting) -->
      <slot v-if="showLeftSpinner" name="loading">
        <svg
          :class="iconClasses"
          class="animate-spin"
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
          aria-hidden="true"
        >
          <circle
            class="opacity-25"
            cx="12"
            cy="12"
            r="10"
            stroke="currentColor"
            stroke-width="4"
          />
          <path
            class="opacity-75"
            fill="currentColor"
            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
          />
        </svg>
      </slot>

      <!-- Left Icon (when not loading on left) -->
      <template v-else-if="hasLeftIcon">
        <slot name="icon-left">
          <slot name="leading">
            <slot v-if="props.iconPosition === 'left' && $slots.icon" name="icon" />
            <component
              :is="leftIconComponent"
              v-else-if="leftIconComponent"
              :class="iconClasses"
              aria-hidden="true"
            />
          </slot>
        </slot>
      </template>

      <!-- Main / default text slot -->
      <span v-if="$slots.default">
        <slot />
      </span>

      <!-- Right Spinner (when waiting on right) -->
      <slot v-if="showRightSpinner" name="loading">
        <svg
          :class="iconClasses"
          class="animate-spin"
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
          aria-hidden="true"
        >
          <circle
            class="opacity-25"
            cx="12"
            cy="12"
            r="10"
            stroke="currentColor"
            stroke-width="4"
          />
          <path
            class="opacity-75"
            fill="currentColor"
            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
          />
        </svg>
      </slot>

      <!-- Right Icon (when not loading on right) -->
      <template v-else-if="hasRightIcon">
        <slot name="icon-right">
          <slot name="trailing">
            <slot v-if="props.iconPosition === 'right' && $slots.icon" name="icon" />
            <component
              :is="rightIconComponent"
              v-else-if="rightIconComponent"
              :class="iconClasses"
              aria-hidden="true"
            />
          </slot>
        </slot>
      </template>
    </template>
  </button>
</template>
