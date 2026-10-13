<script setup lang="ts">
import { computed, useId } from 'vue'
import type { InputSize, InputVariant, UIInputProps } from './input.types'

export type { InputSize, InputVariant, UIInputProps }

const props = withDefaults(defineProps<UIInputProps>(), {
  size: 'md',
  variant: 'default',
  type: 'text',
  id: undefined,
  name: undefined,
  label: undefined,
  placeholder: undefined,
  hint: undefined,
  error: false,
  disabled: false,
  readonly: false,
  required: false,
  iconLeft: undefined,
  iconRight: undefined,
  iconPosition: 'left',
})

const model = defineModel<string | number>({ default: '' })

const generatedId = useId()
const inputId = computed(() => props.id || generatedId)

const hasError = computed(() => Boolean(props.error))
const errorMessage = computed(() => (typeof props.error === 'string' ? props.error : ''))

const effectiveVariant = computed<InputVariant>(() => {
  if (hasError.value) return 'danger'
  return props.variant
})

const sizeClasses = computed(() => {
  switch (props.size) {
    case 'sm':
      return 'h-8 text-xs px-2.5 rounded-md'
    case 'lg':
      return 'h-12 text-base px-4 rounded-lg'
    case 'md':
    default:
      return 'h-10 text-sm px-3 rounded-md'
  }
})

const iconClasses = computed(() => {
  switch (props.size) {
    case 'sm':
      return 'w-3.5 h-3.5'
    case 'lg':
      return 'w-5 h-5'
    case 'md':
    default:
      return 'w-4 h-4'
  }
})

const paddingClasses = computed(() => {
  const hasLeft = Boolean(props.iconLeft)
  const hasRight = Boolean(props.iconRight)

  switch (props.size) {
    case 'sm':
      return [
        hasLeft ? 'ps-8' : '',
        hasRight ? 'pe-8' : '',
      ]
    case 'lg':
      return [
        hasLeft ? 'ps-11' : '',
        hasRight ? 'pe-11' : '',
      ]
    case 'md':
    default:
      return [
        hasLeft ? 'ps-9' : '',
        hasRight ? 'pe-9' : '',
      ]
  }
})

const variantClasses = computed(() => {
  switch (effectiveVariant.value) {
    case 'danger':
      return 'border-danger text-danger placeholder:text-danger/60 focus-visible:ring-danger focus-visible:border-danger'
    case 'ghost':
      return 'border-transparent bg-transparent hover:bg-ghost-hover focus-visible:border-input-border focus-visible:bg-input-bg focus-visible:ring-input-focus'
    case 'secondary':
      return 'border-secondary-hover bg-secondary text-secondary-foreground placeholder:text-secondary-foreground/60 focus-visible:ring-secondary focus-visible:border-secondary-active'
    case 'primary':
      return 'border-primary bg-input-bg text-input-text placeholder:text-input-placeholder focus-visible:ring-primary focus-visible:border-primary'
    case 'default':
    default:
      return 'border-input-border bg-input-bg text-input-text placeholder:text-input-placeholder hover:border-input-border-hover focus-visible:border-input-focus focus-visible:ring-input-focus'
  }
})

const inputClasses = computed(() => [
  'w-full border transition-colors duration-150 outline-none select-text',
  'focus-visible:ring-2 focus-visible:ring-offset-1',
  'disabled:opacity-50 disabled:cursor-not-allowed disabled:bg-secondary/40',
  'read-only:cursor-default read-only:bg-secondary/20',
  sizeClasses.value,
  paddingClasses.value,
  variantClasses.value,
])
</script>

<template>
  <div class="flex flex-col gap-1.5 w-full">
    <!-- Label -->
    <label
      v-if="label || $slots.label"
      :for="inputId"
      class="text-sm font-medium text-input-text flex items-center gap-1 select-none"
    >
      <slot name="label">{{ label }}</slot>
      <span v-if="required" class="text-danger" aria-hidden="true">*</span>
    </label>

    <!-- Input container with relative positioning for icons -->
    <div class="relative flex items-center w-full">
      <!-- Left Icon -->
      <div
        v-if="iconLeft || $slots['icon-left'] || $slots.leading"
        class="absolute start-3 flex items-center pointer-events-none text-input-placeholder"
      >
        <slot name="icon-left">
          <slot name="leading">
            <component :is="iconLeft" :class="iconClasses" aria-hidden="true" />
          </slot>
        </slot>
      </div>

      <!-- Native Input -->
      <input
        :id="inputId"
        v-model="model"
        :type="type"
        :name="name"
        :placeholder="placeholder"
        :disabled="disabled"
        :readonly="readonly"
        :required="required"
        :aria-invalid="hasError"
        :aria-describedby="hasError ? `${inputId}-error` : hint ? `${inputId}-hint` : undefined"
        :class="inputClasses"
      />

      <!-- Right Icon -->
      <div
        v-if="iconRight || $slots['icon-right'] || $slots.trailing"
        class="absolute end-3 flex items-center pointer-events-none text-input-placeholder"
      >
        <slot name="icon-right">
          <slot name="trailing">
            <component :is="iconRight" :class="iconClasses" aria-hidden="true" />
          </slot>
        </slot>
      </div>
    </div>

    <!-- Error or Hint message -->
    <p
      v-if="hasError && (errorMessage || $slots.error)"
      :id="`${inputId}-error`"
      class="text-xs text-danger flex items-center gap-1"
    >
      <slot name="error">{{ errorMessage }}</slot>
    </p>
    <p
      v-else-if="hint || $slots.hint"
      :id="`${inputId}-hint`"
      class="text-xs text-input-placeholder"
    >
      <slot name="hint">{{ hint }}</slot>
    </p>
  </div>
</template>
