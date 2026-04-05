import { defineStore } from 'pinia'

export const useSessionStore = defineStore('session', {
    state: () => ({
        currentRole: 'volunteer',
    }),
    actions: {
        setRole(role) {
            this.currentRole = role
        },
    },
    
})