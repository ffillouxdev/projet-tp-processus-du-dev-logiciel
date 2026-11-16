<script setup lang="ts">
export interface BracketPlayer {
  id: string | number
  name: string
  score?: number
  status?: 'winner' | 'loser' | 'pending'
}

defineProps<{
  players: readonly [BracketPlayer, BracketPlayer]
}>()

defineEmits<{
  (e: 'click'): void
}>()
</script>

<template>
  <article
    class="cursor-pointer overflow-hidden rounded-lg border border-dialog-border bg-dialog-bg shadow-sm transition-all hover:border-primary/50 hover:shadow-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
    tabindex="0"
    role="button"
    @click="$emit('click')"
    @keydown.enter="$emit('click')"
    @keydown.space.prevent="$emit('click')"
  >
    <div class="divide-y divide-dialog-border">
      <div
        v-for="player in players"
        :key="player.id"
        class="flex min-h-12 items-center gap-2 px-3 py-1.5"
        :class="{
          'bg-primary/5': player.status === 'winner',
          'opacity-55': player.status === 'loser',
        }"
      >
        <p
          class="min-w-0 flex-1 truncate text-xs font-semibold text-gray-900 dark:text-gray-100"
          :class="{ 'text-primary': player.status === 'winner' }"
        >
          {{ player.name }}
        </p>
        <span
          v-if="player.score !== undefined"
          class="min-w-4 text-center text-sm font-bold text-gray-900 dark:text-gray-100"
          :class="{ 'text-primary': player.status === 'winner' }"
        >
          {{ player.score }}
        </span>
        <span v-else-if="player.status === 'pending'" class="text-[10px] text-gray-500 dark:text-gray-400">-</span>
      </div>
    </div>
  </article>
</template>
