<script setup lang="ts">
import { computed, provide, toRef } from 'vue'
import {
  buttonGroupKey,
  type ButtonGroupOrientation,
  type UIButtonGroupProps,
} from './button.types'

export type { ButtonGroupOrientation, UIButtonGroupProps }

const props = withDefaults(defineProps<UIButtonGroupProps>(), {
  size: undefined,
  variant: undefined,
  disabled: false,
  orientation: 'horizontal',
  divided: true,
  attached: true,
  ariaLabel: 'Button group',
  fullWidth: false,
})

provide(buttonGroupKey, {
  size: toRef(props, 'size'),
  variant: toRef(props, 'variant'),
  disabled: toRef(props, 'disabled'),
  orientation: toRef(props, 'orientation'),
})

const isVertical = computed(() => props.orientation === 'vertical')

const divideClasses = computed(() => {
  if (!props.divided || !props.attached) return ''

  const dividerColorClass = (() => {
    switch (props.variant) {
      case 'secondary':
        return 'divide-secondary-active'
      case 'ghost':
        return 'divide-ghost-active'
      case 'danger':
        return 'divide-danger-active'
      case 'primary':
        return 'divide-primary-active'
      default:
        return 'divide-btn-group-divider'
    }
  })()

  return isVertical.value
    ? `divide-y ${dividerColorClass}`
    : `divide-x ${dividerColorClass}`
})

const layoutClasses = computed(() => {
  if (isVertical.value) {
    return [
      'flex-col',
      props.fullWidth ? 'flex w-full [&>*]:w-full' : 'inline-flex',
    ]
  }
  return [
    'flex-row items-center',
    props.fullWidth ? 'flex w-full [&>*]:flex-1' : 'inline-flex',
  ]
})

const attachedClasses = computed(() => {
  if (!props.attached) {
    return isVertical.value ? 'gap-2' : 'gap-2'
  }

  if (isVertical.value) {
    return [
      'isolate',
      '[&>*:first-child:not(:only-child)]:rounded-b-none',
      '[&>*:not(:first-child):not(:last-child)]:rounded-none',
      '[&>*:last-child:not(:only-child)]:rounded-t-none',
      '[&>*:not(:first-child)]:-mt-px',
      '[&>*]:relative',
      '[&>*:hover]:z-10',
      '[&>*:focus-visible]:z-20',
      '[&>*:active]:z-10',
      '[&>*:disabled]:z-0',
    ]
  }

  return [
    'isolate',
    '[&>*:first-child:not(:only-child)]:rounded-r-none',
    '[&>*:not(:first-child):not(:last-child)]:rounded-none',
    '[&>*:last-child:not(:only-child)]:rounded-l-none',
    '[&>*:not(:first-child)]:-ms-px',
    '[&>*]:relative',
    '[&>*:hover]:z-10',
    '[&>*:focus-visible]:z-20',
    '[&>*:active]:z-10',
    '[&>*:disabled]:z-0',
  ]
})

const groupClasses = computed(() => [
  layoutClasses.value,
  attachedClasses.value,
  divideClasses.value,
])
</script>

<template>
  <div
    role="group"
    :aria-orientation="orientation"
    :aria-label="ariaLabel"
    :class="groupClasses"
  >
    <slot />
  </div>
</template>
