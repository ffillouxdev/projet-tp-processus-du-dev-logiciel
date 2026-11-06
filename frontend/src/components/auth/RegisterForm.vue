<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { UIButton, UIInput } from '@/components/ui'

export interface RegisterFormData {
  email: string
  username: string
  fullName: string
  password: string
}

const emit = defineEmits<{
  (e: 'submit', data: RegisterFormData): void
}>()

const form = reactive<RegisterFormData>({
  email: '',
  username: '',
  fullName: '',
  password: '',
})

const passwordConfirmation = ref('')
const hasSubmitted = ref(false)
const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/u
const usernamePattern = /^[a-zA-Z0-9_.-]+$/u
const passwordPattern = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z\d]).{10,}$/u

const passwordError = computed(() => {
  if (!hasSubmitted.value) return false
  if (!form.password) return 'Le mot de passe est obligatoire.'
  if (!passwordPattern.test(form.password)) {
    return 'Le mot de passe doit contenir au moins 10 caractères, une majuscule, une minuscule, un chiffre et un caractère spécial.'
  }
  return false
})

const confirmationError = computed(() => {
  if (!hasSubmitted.value) return false
  if (!passwordConfirmation.value) return 'Veuillez confirmer votre mot de passe.'
  if (passwordConfirmation.value !== form.password) {
    return 'Les mots de passe ne correspondent pas.'
  }
  return false
})

const isFormValid = computed(() => (
  emailPattern.test(form.email.trim())
  && form.username.length >= 3
  && form.username.length <= 50
  && usernamePattern.test(form.username)
  && Boolean(form.fullName.trim())
  && passwordPattern.test(form.password)
  && passwordConfirmation.value === form.password
))

function handleSubmit() {
  hasSubmitted.value = true
  if (passwordError.value || confirmationError.value) return

  emit('submit', { ...form })
}
</script>

<template>
  <form class="flex flex-col gap-4" @submit.prevent="handleSubmit">
    <!-- 1. Email -->
    <UIInput
      v-model="form.email"
      type="email"
      name="email"
      label="Adresse email"
      placeholder="nom@exemple.com"
      required
    />

    <!-- 2. Nom d'utilisateur (Username) -->
    <UIInput
      v-model="form.username"
      type="text"
      name="username"
      label="Nom d'utilisateur"
      placeholder="ex: player_one"
      hint="3 à 50 caractères (lettres, chiffres, tirets, points)"
      required
    />

    <!-- 3. Nom complet (Full name) -->
    <UIInput
      v-model="form.fullName"
      type="text"
      name="fullName"
      label="Nom complet"
      placeholder="ex: Jean Dupont"
      required
    />

    <!-- 4. Mot de passe (Password) -->
    <UIInput
      v-model="form.password"
      type="password"
      name="password"
      label="Mot de passe"
      placeholder="••••••••"
      hint="10 caractères minimum avec une majuscule, une minuscule, un chiffre et un caractère spécial"
      :error="passwordError"
      required
    />

    <!-- 5. Confirmation du mot de passe -->
    <UIInput
      v-model="passwordConfirmation"
      type="password"
      name="passwordConfirmation"
      label="Confirmer le mot de passe"
      placeholder="••••••••"
      :error="confirmationError"
      required
    />

    <!-- Bouton de soumission -->
    <UIButton
      type="submit"
      variant="primary"
      size="lg"
      class="w-full mt-2"
      :disabled="!isFormValid"
    >
      Créer un compte
    </UIButton>
  </form>
</template>
