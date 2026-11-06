<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { UIButton, UIInput } from '@/components/ui'

export interface LoginFormData {
  identifier: string
  password: string
}

const emit = defineEmits<{
  (e: 'submit', data: LoginFormData): void
}>()

const form = reactive<LoginFormData>({
  identifier: '',
  password: '',
})

const hasSubmitted = ref(false)

const identifierError = computed(() => {
  if (!hasSubmitted.value || form.identifier.trim()) return false
  return 'L’adresse email ou le nom d’utilisateur est obligatoire.'
})

const passwordError = computed(() => {
  if (!hasSubmitted.value || form.password) return false
  return 'Le mot de passe est obligatoire.'
})

const isFormValid = computed(() => form.identifier.trim().length >= 3 && Boolean(form.password))

function handleSubmit() {
  hasSubmitted.value = true
  if (!isFormValid.value) return

  emit('submit', {
    identifier: form.identifier.trim(),
    password: form.password,
  })
}
</script>

<template>
  <form class="flex flex-col gap-4" @submit.prevent="handleSubmit">
    <UIInput
      v-model="form.identifier"
      type="text"
      name="identifier"
      label="Email ou nom d'utilisateur"
      placeholder="nom@exemple.com ou player_one"
      :error="identifierError"
      required
    />

    <UIInput
      v-model="form.password"
      type="password"
      name="password"
      label="Mot de passe"
      placeholder="••••••••"
      :error="passwordError"
      required
    />

    <UIButton
      type="submit"
      variant="primary"
      size="lg"
      class="w-full mt-2"
      :disabled="!isFormValid"
    >
      Se connecter
    </UIButton>
  </form>
</template>
