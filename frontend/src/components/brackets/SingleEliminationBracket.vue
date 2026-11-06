<script setup lang="ts">
import { computed } from 'vue'
import BracketMatch from './BracketMatch.vue'
import type {
  SingleEliminationMatch,
  SingleEliminationMatches,
} from './single-elimination.types'

const props = defineProps<{
  matches: SingleEliminationMatches
  title?: string
  embedded?: boolean
}>()

const rounds = computed(() => {
  const grouped = new Map<string, SingleEliminationMatch[]>()

  for (const match of props.matches) {
    const roundMatches = grouped.get(match.round) ?? []
    roundMatches.push(match)
    grouped.set(match.round, roundMatches)
  }

  return [...grouped.entries()].map(([name, roundMatches]) => ({
    name,
    matches: roundMatches,
  }))
})
</script>

<template>
  <section class="min-w-0" aria-label="Bracket à élimination directe">
    <h2 v-if="title" class="mb-2 text-sm font-semibold text-gray-900 dark:text-gray-100">
      {{ title }}
    </h2>
    <div
      :class="
        embedded
          ? 'overflow-visible'
          : 'max-h-144 overflow-auto rounded-lg border border-dialog-border bg-secondary/20 p-4 overscroll-contain [scrollbar-width:thin] touch-pan-x touch-pan-y'
      "
    >
      <div class="flex min-h-[24rem] min-w-max items-stretch gap-14 pb-4">
        <div
          v-for="round in rounds"
          :key="round.name"
          class="flex min-h-[24rem] w-52 shrink-0 flex-col justify-center gap-6"
        >
          <h3 class="text-center text-xs font-bold text-gray-500 dark:text-gray-400">
            {{ round.name }}
          </h3>
          <div class="flex flex-col justify-center gap-6">
            <BracketMatch
              v-for="match in round.matches"
              :key="match.id"
              :players="match.players"
            />
          </div>
        </div>
      </div>
    </div>
  </section>
</template>
