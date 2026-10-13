<script setup lang="ts">
import { computed, useId } from 'vue'
import type { CheckboxSize, CheckboxVariant, UICheckboxProps } from './input.types'

export type { CheckboxSize, CheckboxVariant, UICheckboxProps }

const props = withDefaults(defineProps<UICheckboxProps>(), {
  size: 'md',
  variant: 'primary',
  id: undefined,
  name: undefined,
  label: undefined,
  hint: undefined,
  disabled: false,
  required: false,
  indeterminate: false,
  value: undefined,
  error: false,
})

const model = defineModel<boolean | unknown[]>({ default: false })

const generatedId = useId()
const checkboxId = computed(() => props.id || generatedId)

const isChecked = computed(() => {
  if (Array.isArray(model.value)) {
    return props.value !== undefined && model.value.includes(props.value)
  }
  return Boolean(model.value)
})

function handleChange(event: Event) {
  if (props.disabled) return
  const target = event.target as HTMLInputElement

  if (Array.isArray(model.value)) {
    const list = [...model.value]
    if (target.checked) {
      if (props.value !== undefined && !list.includes(props.value)) {
        list.push(props.value)
      }
    } else {
      if (props.value !== undefined) {
        const index = list.indexOf(props.value)
        if (index > -1) {
          list.splice(index, 1)
        }
      }
    }
    model.value = list
  } else {
    model.value = target.checked
  }
}

const sizeClasses = computed(() => {
  switch (props.size) {
    case 'sm':
      return 'w-4 h-4 rounded text-xs'
    case 'lg':
      return 'w-6 h-6 rounded-md text-base'
    case 'md':
    default:
      return 'w-5 h-5 rounded-md text-sm'
  }
})

const iconClasses = computed(() => {
  switch (props.size) {
    case 'sm':
      return 'w-3 h-3'
    case 'lg':
      return 'w-4.5 h-4.5'
    case 'md':
    default:
      return 'w-3.5 h-3.5'
  }
})

const variantClasses = computed(() => {
  if (props.error) {
    return isChecked.value || props.indeterminate
      ? 'bg-danger border-danger text-danger-foreground focus-visible:ring-danger'
      : 'bg-input-bg border-danger text-transparent hover:border-danger'
  }

  if (isChecked.value || props.indeterminate) {
    switch (props.variant) {
      case 'secondary':
        return 'bg-secondary border-secondary-hover text-secondary-foreground focus-visible:ring-secondary'
      case 'danger':
        return 'bg-danger border-danger text-danger-foreground focus-visible:ring-danger'
      case 'ghost':
        return 'bg-ghost-hover border-ghost-foreground text-ghost-foreground focus-visible:ring-ghost'
      case 'primary':
      default:
        return 'bg-primary border-primary text-primary-foreground focus-visible:ring-primary'
    }
  }

  return 'bg-input-bg border-input-border text-transparent hover:border-input-border-hover'
})

const checkboxBoxClasses = computed(() => [
  'inline-flex items-center justify-center border transition-colors duration-150 shrink-0 cursor-pointer select-none',
  'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-1',
  'disabled:opacity-50 disabled:cursor-not-allowed',
  sizeClasses.value,
  variantClasses.value,
])
</script>

<template>
  <div class="flex items-start gap-2.5">
    <div class="relative flex items-center justify-center mt-0.5">
      <!-- Hidden native input for keyboard/accessibility handling -->
      <input
        :id="checkboxId"
        type="checkbox"
        :name="name"
        :checked="isChecked"
        :disabled="disabled"
        :required="required"
        :aria-invalid="Boolean(error)"
        class="sr-only peer"
        @change="handleChange"
      />

      <!-- Custom styled checkbox box -->
      <label
        :for="checkboxId"
        :class="checkboxBoxClasses"
        class="peer-focus-visible:ring-2 peer-focus-visible:ring-offset-1"
        :aria-hidden="true"
      >
        <!-- Indeterminate icon (minus / dash) -->
        <svg
          v-if="indeterminate"
          :class="iconClasses"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="3"
          stroke-linecap="round"
          stroke-linejoin="round"
        >
          <line x1="5" y1="12" x2="19" y2="12" />
        </svg>

        <!-- Checked checkmark icon -->
        <svg
          v-else-if="isChecked"
          :class="iconClasses"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="3"
          stroke-linecap="round"
          stroke-linejoin="round"
        >
          <polyline points="20 6 9 17 4 12" />
        </svg>
      </label>
    </div>

    <!-- Label & Hint -->
    <div v-if="label || $slots.default || hint || $slots.hint" class="flex flex-col gap-0.5">
      <label
        :for="checkboxId"
        :class="[
          'text-sm font-medium text-input-text select-none cursor-pointer',
          disabled ? 'opacity-50 cursor-not-allowed' : '',
        ]"
      >
        <slot>{{ label }}</slot>
        <span v-if="required" class="text-danger ms-1" aria-hidden="true">*</span>
      </label>
      <p v-if="hint || $slots.hint" class="text-xs text-input-placeholder">
        <slot name="hint">{{ hint }}</slot>
      </p>
      <p v-if="typeof error === 'string' && error" class="text-xs text-danger">
        {{ error }}
      </p>
    </div>
  </div>
</template>
