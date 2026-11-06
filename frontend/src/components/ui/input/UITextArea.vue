<script setup lang="ts">
import { computed, useId } from 'vue'
import type { InputSize, InputVariant, UITextAreaProps } from './input.types'

export type { InputSize, InputVariant, UITextAreaProps }

const props = withDefaults(defineProps<UITextAreaProps>(), {
  size: 'md',
  variant: 'default',
  id: undefined,
  name: undefined,
  label: undefined,
  placeholder: undefined,
  hint: undefined,
  error: false,
  disabled: false,
  readonly: false,
  required: false,
  rows: 3,
  resize: 'vertical',
  maxlength: undefined,
  showCount: false,
})

const model = defineModel<string>({ default: '' })

const generatedId = useId()
const textareaId = computed(() => props.id || generatedId)

const hasError = computed(() => Boolean(props.error))
const errorMessage = computed(() => (typeof props.error === 'string' ? props.error : ''))

const effectiveVariant = computed<InputVariant>(() => {
  if (hasError.value) return 'danger'
  return props.variant
})

const sizeClasses = computed(() => {
  switch (props.size) {
    case 'sm':
      return 'text-xs px-2.5 py-1.5 rounded-md min-h-[64px]'
    case 'lg':
      return 'text-base px-4 py-3 rounded-lg min-h-[120px]'
    case 'md':
    default:
      return 'text-sm px-3 py-2 rounded-md min-h-[88px]'
  }
})

const resizeClasses = computed(() => {
  switch (props.resize) {
    case 'none':
      return 'resize-none'
    case 'horizontal':
      return 'resize-x'
    case 'both':
      return 'resize'
    case 'vertical':
    default:
      return 'resize-y'
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

const textareaClasses = computed(() => [
  'w-full border transition-colors duration-150 outline-none select-text',
  'focus-visible:ring-2 focus-visible:ring-offset-1',
  'disabled:opacity-50 disabled:cursor-not-allowed disabled:bg-secondary/40',
  'read-only:cursor-default read-only:bg-secondary/20',
  sizeClasses.value,
  resizeClasses.value,
  variantClasses.value,
])

const currentLength = computed(() => (model.value ? String(model.value).length : 0))
</script>

<template>
  <div class="flex flex-col gap-1.5 w-full">
    <!-- Label and Character Count -->
    <div v-if="label || $slots.label || (showCount && maxlength)" class="flex items-center justify-between">
      <label
        v-if="label || $slots.label"
        :for="textareaId"
        class="text-sm font-medium text-input-text flex items-center gap-1 select-none"
      >
        <slot name="label">{{ label }}</slot>
        <span v-if="required" class="text-danger" aria-hidden="true">*</span>
      </label>
      <span v-if="showCount && maxlength" class="text-xs text-input-placeholder ms-auto">
        {{ currentLength }} / {{ maxlength }}
      </span>
    </div>

    <!-- Native TextArea -->
    <textarea
      :id="textareaId"
      v-model="model"
      :name="name"
      :rows="rows"
      :maxlength="maxlength"
      :placeholder="placeholder"
      :disabled="disabled"
      :readonly="readonly"
      :required="required"
      :aria-invalid="hasError"
      :aria-describedby="hasError ? `${textareaId}-error` : hint ? `${textareaId}-hint` : undefined"
      :class="textareaClasses"
    />

    <!-- Error or Hint message -->
    <p
      v-if="hasError && (errorMessage || $slots.error)"
      :id="`${textareaId}-error`"
      class="text-xs text-danger flex items-center gap-1"
    >
      <slot name="error">{{ errorMessage }}</slot>
    </p>
    <p
      v-else-if="hint || $slots.hint"
      :id="`${textareaId}-hint`"
      class="text-xs text-input-placeholder"
    >
      <slot name="hint">{{ hint }}</slot>
    </p>
  </div>
</template>
