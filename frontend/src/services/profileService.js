import api from './api';

export const profileService = {
  /**
   * Fetch the authenticated user's financial profile.
   * Returns null if 404 (user has not created a profile yet).
   */
  async getProfile() {
    try {
      const response = await api.get('/api/v1/profile');
      return response.data;
    } catch (err) {
      if (err.message && err.message.toLowerCase().includes('not found')) {
        return null;
      }
      throw err;
    }
  },

  /**
   * Create or replace the authenticated user's financial profile.
   */
  async saveProfile(profileData) {
    const response = await api.put('/api/v1/profile', profileData);
    return response.data;
  },

  /**
   * Partially update the authenticated user's financial profile.
   */
  async patchProfile(partialData) {
    const response = await api.patch('/api/v1/profile', partialData);
    return response.data;
  },
};

export default profileService;
