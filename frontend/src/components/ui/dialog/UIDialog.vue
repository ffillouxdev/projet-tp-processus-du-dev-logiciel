<script setup lang="ts">
import { computed, onMounted, onUnmounted, useId, watch } from 'vue'
import type { DialogSize, UIDialogProps } from './dialog.types'

export type { DialogSize, UIDialogProps }

const props = withDefaults(defineProps<UIDialogProps>(), {
  title: undefined,
  description: undefined,
  canClose: true,
  size: 'md',
  teleportTo: 'body',
  closeOnEsc: true,
})

const emit = defineEmits<{
  (e: 'open'): void
  (e: 'close'): void
}>()

const isOpen = defineModel<boolean>({ default: false })

const generatedId = useId()
const titleId = computed(() => `${generatedId}-title`)
const descriptionId = computed(() => `${generatedId}-desc`)

function openDialog() {
  isOpen.value = true
  emit('open')
}

function closeDialog() {
  if (!props.canClose) return
  isOpen.value = false
  emit('close')
}

function handleBackdropClick(event: MouseEvent) {
  if (props.canClose && event.target === event.currentTarget) {
    closeDialog()
  }
}

function handleKeydown(event: KeyboardEvent) {
  if (event.key === 'Escape' && isOpen.value && props.canClose && props.closeOnEsc) {
    closeDialog()
  }
}

watch(isOpen, (open) => {
  if (typeof document !== 'undefined') {
    if (open) {
      document.body.style.overflow = 'hidden'
    } else {
      document.body.style.overflow = ''
    }
  }
})

onMounted(() => {
  if (typeof window !== 'undefined') {
    window.addEventListener('keydown', handleKeydown)
  }
})

onUnmounted(() => {
  if (typeof window !== 'undefined') {
    window.removeEventListener('keydown', handleKeydown)
  }
  if (typeof document !== 'undefined') {
    document.body.style.overflow = ''
  }
})

const sizeClasses = computed(() => {
  switch (props.size) {
    case 'sm':
      return 'max-w-sm'
    case 'lg':
      return 'max-w-2xl'
    case 'xl':
      return 'max-w-4xl'
    case 'full':
      return 'max-w-[95vw] h-[90vh]'
    case 'md':
    default:
      return 'max-w-lg'
  }
})
</script>

<template>
  <!-- Trigger Slot -->
  <div v-if="$slots.trigger" class="inline-block" @click="openDialog">
    <slot name="trigger" :open="openDialog" :close="closeDialog" />
  </div>

  <!-- Teleported Modal -->
  <Teleport :to="teleportTo">
    <Transition
      enter-active-class="transition duration-200 ease-out"
      enter-from-class="opacity-0"
      enter-to-class="opacity-100"
      leave-active-class="transition duration-150 ease-in"
      leave-from-class="opacity-100"
      leave-to-class="opacity-0"
    >
      <div
        v-if="isOpen"
        class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-dialog-overlay"
        aria-hidden="true"
        @click="handleBackdropClick"
      >
        <!-- Dialog Panel -->
        <Transition
          enter-active-class="transition duration-200 ease-out"
          enter-from-class="opacity-0 scale-95"
          enter-to-class="opacity-100 scale-100"
          leave-active-class="transition duration-150 ease-in"
          leave-from-class="opacity-100 scale-100"
          leave-to-class="opacity-0 scale-95"
        >
          <div
            v-if="isOpen"
            role="dialog"
            aria-modal="true"
            :aria-labelledby="title || $slots.title ? titleId : undefined"
            :aria-describedby="description || $slots.description ? descriptionId : undefined"
            :class="[
              'relative w-full bg-dialog-bg text-dialog-text border border-dialog-border rounded-xl shadow-xl flex flex-col max-h-[90vh] overflow-hidden select-text',
              sizeClasses,
            ]"
            @click.stop
          >
            <!-- Header (Title, Description, and Close 'X' Button) -->
            <div
              v-if="title || description || $slots.header || $slots.title || $slots.description || canClose"
              class="p-6 pb-4 border-b border-dialog-border relative pe-12"
            >
              <slot name="header">
                <h2
                  v-if="title || $slots.title"
                  :id="titleId"
                  class="text-lg font-semibold text-dialog-text leading-tight"
                >
                  <slot name="title">{{ title }}</slot>
                </h2>
                <p
                  v-if="description || $slots.description"
                  :id="descriptionId"
                  class="text-sm text-dialog-muted mt-1.5 leading-normal"
                >
                  <slot name="description">{{ description }}</slot>
                </p>
              </slot>

              <!-- Close 'X' Button (visible when canClose is true) -->
              <button
                v-if="canClose"
                type="button"
                aria-label="Fermer la boîte de dialogue"
                class="absolute top-4 end-4 p-1.5 rounded-lg text-dialog-muted hover:text-dialog-text hover:bg-ghost-hover transition-colors cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
                @click="closeDialog"
              >
                <svg
                  class="w-5 h-5"
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  stroke-width="2"
                  aria-hidden="true"
                >
                  <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            <!-- Content Slot -->
            <div class="p-6 overflow-y-auto flex-1 text-sm text-dialog-text">
              <slot name="content">
                <slot />
              </slot>
            </div>

            <!-- Footer Slot -->
            <div
              v-if="$slots.footer"
              class="p-4 px-6 border-t border-dialog-border flex items-center justify-end gap-3 bg-secondary/15"
            >
              <slot name="footer" :close="closeDialog" />
            </div>
          </div>
        </Transition>
      </div>
    </Transition>
  </Teleport>
</template>
