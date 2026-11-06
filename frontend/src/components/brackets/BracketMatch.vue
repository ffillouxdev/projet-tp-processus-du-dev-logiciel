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

</script>

<template>
  <article
    class="overflow-hidden rounded-lg border border-dialog-border bg-dialog-bg shadow-sm transition-shadow hover:shadow-md"
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
          class="min-w-0 flex-1 truncate text-xs font-semibold text-gray-900"
          :class="{ 'text-primary': player.status === 'winner' }"
        >
          {{ player.name }}
        </p>
        <span
          v-if="player.score !== undefined"
          class="min-w-4 text-center text-sm font-bold text-gray-900"
          :class="{ 'text-primary': player.status === 'winner' }"
        >
          {{ player.score }}
        </span>
        <span v-else-if="player.status === 'pending'" class="text-[10px] text-gray-500">-</span>
      </div>
    </div>
  </article>
</template>
