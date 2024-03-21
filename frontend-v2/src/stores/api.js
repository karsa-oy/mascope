import { api } from '$api'

import { defineStore } from 'pinia'

export const useApiStore = defineStore('api', () => {
    return api;
})