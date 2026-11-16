<script setup lang="ts">
import { computed } from 'vue'
import {
  SingleEliminationBracket,
  type SingleEliminationMatch,
  type SingleEliminationMatches,
} from '@/components/brackets'
import type { TournamentBracketMatch } from '@/composables'

const props = withDefaults(
  defineProps<{
    matches?: TournamentBracketMatch[]
    isMatchInteractive?: (match: TournamentBracketMatch) => boolean
  }>(),
  {
    matches: () => [],
    isMatchInteractive: () => false,
  },
)

const emit = defineEmits<{
  (e: 'selectMatch', match: TournamentBracketMatch): void
}>()

function checkMatchInteractive(matchId: string | number): boolean {
  const match = props.matches.find((m) => m.id === matchId)
  if (!match) return false
  return props.isMatchInteractive(match)
}

function handleSelectMatch(matchId: string | number) {
  const match = props.matches.find((m) => m.id === matchId)
  if (match) {
    emit('selectMatch', match)
  }
}

const bracketMatches = computed<SingleEliminationMatches>(() =>
  props.matches.map((match): SingleEliminationMatch => {
    const [firstPlayer, secondPlayer] = match.players

    return {
      id: match.id,
      round: match.round,
      players: [
        {
          ...firstPlayer,
          id: firstPlayer.id ?? `${match.id}-player-1`,
          score: firstPlayer.score ?? undefined,
        },
        {
          ...secondPlayer,
          id: secondPlayer.id ?? `${match.id}-player-2`,
          score: secondPlayer.score ?? undefined,
        },
      ],
    }
  }),
)
</script>

<template>
  <SingleEliminationBracket
    v-if="bracketMatches.length"
    :matches="bracketMatches"
    :is-match-interactive="checkMatchInteractive"
    title="Tableau des matchs"
    @select-match="handleSelectMatch"
  />
  <p v-else class="rounded-xl border border-dashed border-dialog-border p-6 text-center text-dialog-muted">
    Le bracket sera disponible lorsque le tournoi commencera.
  </p>
</template>
