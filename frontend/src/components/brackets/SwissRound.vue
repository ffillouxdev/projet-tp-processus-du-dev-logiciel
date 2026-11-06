<script setup lang="ts">
import { computed } from 'vue'
import BracketMatch from './BracketMatch.vue'
import type { SwissMatchResult, SwissRoundResults } from './swiss-round.types'

const props = defineProps<{
  results: SwissRoundResults
  title?: string
}>()

const groups = computed(() => {
  const grouped = new Map<string, SwissMatchResult[]>()

  for (const result of props.results) {
    const matches = grouped.get(result.group) ?? []
    matches.push(result)
    grouped.set(result.group, matches)
  }

  return [...grouped.entries()].map(([label, matches]) => ({ label, matches }))
})

const columns = computed(() => {
  const grouped = new Map<number, typeof groups.value>()

  for (const group of groups.value) {
    const scoreTotal = group.label.split(':').reduce((total, score) => total + Number(score), 0)
    const column = grouped.get(scoreTotal) ?? []
    column.push(group)
    grouped.set(scoreTotal, column)
  }

  return [...grouped.entries()]
    .sort(([firstTotal], [secondTotal]) => firstTotal - secondTotal)
    .map(([scoreTotal, columnGroups]) => ({ scoreTotal, groups: columnGroups }))
})
</script>

<template>
  <section class="min-w-0" aria-label="Round suisse">
    <h2 v-if="title" class="mb-2 text-sm font-semibold text-gray-900">{{ title }}</h2>
    <div
      class="max-h-144 overflow-auto rounded-lg border border-dialog-border bg-secondary/20 p-4 overscroll-contain [scrollbar-width:thin] touch-pan-x touch-pan-y"
    >
      <div class="flex min-h-192 min-w-max items-stretch gap-14 pb-4">
        <div
          v-for="column in columns"
          :key="column.scoreTotal"
          class="relative flex min-h-192 w-52 shrink-0 flex-col justify-center gap-6"
        >
          <div
            v-for="group in column.groups"
            :key="group.label"
            class="rounded-xl border border-dialog-border/70 bg-dialog-bg/60 p-2"
          >
            <h3 class="mb-2 text-center text-xs font-bold text-gray-500">{{ group.label }}</h3>
            <div class="flex flex-col gap-2">
              <BracketMatch
                v-for="result in group.matches"
                :key="result.id"
                :players="result.players"
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>
