import type { BracketPlayer } from './BracketMatch.vue'

export interface SingleEliminationMatch {
  id: string | number
  round: string
  players: readonly [BracketPlayer, BracketPlayer]
}

export type SingleEliminationMatches = readonly SingleEliminationMatch[]
