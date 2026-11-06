<script setup lang="ts">
import SingleEliminationBracket from './SingleEliminationBracket.vue'
import BracketMatch from './BracketMatch.vue'
import type { DoubleEliminationBracketData } from './double-elimination.types'

defineProps<{
  bracket: DoubleEliminationBracketData
  title?: string
}>()
</script>

<template>
  <section class="min-w-0" aria-label="Bracket à double élimination">
    <h2 v-if="title" class="mb-2 text-sm font-semibold text-gray-900 dark:text-gray-100">
      {{ title }}
    </h2>
    <div class="max-h-144 overflow-auto rounded-lg border border-dialog-border bg-secondary/20 p-4 overscroll-contain [scrollbar-width:thin] touch-pan-x touch-pan-y">
      <div class="grid min-w-max grid-cols-[auto_auto] gap-x-14 gap-y-4 pb-4">
        <div class="col-span-2">
          <h3 class="mb-2 text-xs font-bold uppercase tracking-wide text-primary">
            Bracket des gagnants
          </h3>
          <SingleEliminationBracket :matches="bracket.initialMatches" :embedded="true" />
        </div>

        <div class="col-span-2">
          <h3 class="mb-2 text-xs font-bold uppercase tracking-wide text-danger">
            Bracket des perdants
          </h3>
          <div class="flex items-center gap-14">
            <SingleEliminationBracket :matches="bracket.losersMatches" :embedded="true" />
            <div v-if="bracket.losersFinal" class="w-52 shrink-0">
              <h3 class="mb-2 text-center text-xs font-bold uppercase tracking-wide text-danger">
                Finale perdants
              </h3>
              <BracketMatch :players="bracket.losersFinal.players" />
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>
