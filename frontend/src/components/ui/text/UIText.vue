<script setup lang="ts">
import { computed } from 'vue';

const props = withDefaults(defineProps<{
  type?: 'paragraph' | 'subtitle' | 'subtext' | ''
}>(), {
  type: 'paragraph'
});

const tag = computed(() => {
  switch (props.type) {
    case 'paragraph':
      return 'p';
    case 'subtitle':
      return 'h2';
    case 'subtext':
      return 'span';
    default:
      return 'p';
  }
});

const classes = computed(() => {
  switch (props.type) {
    case 'paragraph':
      return 'text-base md:text-lg lg:text-xl';
    case 'subtitle':
      return 'text-lg md:text-xl lg:text-2xl font-semibold';
    case 'subtext':
      return 'text-sm md:text-base lg:text-lg text-gray-600 dark:text-gray-400';
    default:
      return '';
  }
});
</script>

<template>
  <component :is="tag" :class="classes">
    <slot />
  </component>
</template>
