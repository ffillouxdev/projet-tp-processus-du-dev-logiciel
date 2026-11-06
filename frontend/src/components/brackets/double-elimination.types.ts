import type {
  SingleEliminationMatch,
  SingleEliminationMatches,
} from './single-elimination.types'

export interface DoubleEliminationBracketData {
  initialMatches: SingleEliminationMatches
  losersMatches: SingleEliminationMatches
  losersFinal?: SingleEliminationMatch
}
