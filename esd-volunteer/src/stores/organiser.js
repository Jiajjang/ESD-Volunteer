import { defineStore } from 'pinia'
import { useLocalStorage } from '@vueuse/core'

export const useOrganiserStore = defineStore('organiser', {
    state: () => ({
        organiserId: useLocalStorage('organiserId', null),
    }),
    actions: {
        setOrganiserId(id) {
            this.organiserId = id
        },
        clearOrganiserId() {
            this.organiserId = null
        },
    },
})