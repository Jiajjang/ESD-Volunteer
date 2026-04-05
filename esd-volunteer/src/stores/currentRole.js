import { defineStore } from 'pinia'
import { useLocalStorage } from '@vueuse/core'

export const useSessionStore = defineStore('session', {
    state: () => ({
        currentRole: useLocalStorage('currentRole', 'volunteer'),
    }),
    actions: {
        setRole(role) {
            this.currentRole = role
        },
        clearRole() {
            this.currentRole = 'volunteer'
        },
    },
})