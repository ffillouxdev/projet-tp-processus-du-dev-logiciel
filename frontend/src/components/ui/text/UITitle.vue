<script setup lang="ts">
import { computed } from 'vue';

const props = withDefaults(defineProps<{
  tag?: 'h1' | 'h2' | 'h3' | 'h4' | 'h5' | 'h6';
}>(), {
  tag: 'h1'
});

const tag = computed(() => props.tag);

const tagClasses = computed(() => {
  switch (props.tag) {
    case 'h1':
      return 'text-4xl md:text-5xl lg:text-6xl';
    case 'h2':
      return 'text-3xl md:text-4xl lg:text-5xl';
    case 'h3':
      return 'text-2xl md:text-3xl lg:text-4xl';
    case 'h4':
      return 'text-xl md:text-2xl lg:text-3xl';
    case 'h5':
      return 'text-lg md:text-xl lg:text-2xl';
    case 'h6':
      return 'text-base md:text-lg lg:text-xl';
    default:
      return '';
  }
});
</script>

<template>
  <component :is="tag" :class="['text-gray-900', 'dark:text-gray-100', 'font-bold', 'mb-4', tagClasses]">
    <slot />
  </component>
</template>
