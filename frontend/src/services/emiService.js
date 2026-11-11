import api from './api';

export const emiService = {
  /**
   * Calculate standard reducing-balance EMI and monthly amortization schedule.
   * All calculations are executed strictly on the FastAPI backend.
   *
   * @param {Object} params
   * @param {number|string} params.principalAmount
   * @param {number|string} params.annualInterestRate
   * @param {number} params.tenureMonths
   * @returns {Promise<Object>} Backend EMICalculationResponse
   */
  async calculateEMI({ principalAmount, annualInterestRate, tenureMonths }) {
    const payload = {
      principal_amount: parseFloat(principalAmount),
      annual_interest_rate: parseFloat(annualInterestRate),
      tenure_months: parseInt(tenureMonths, 10),
    };

    const response = await api.post('/api/v1/emi/calculate', payload);
    return response.data;
  },
};

export default emiService;
