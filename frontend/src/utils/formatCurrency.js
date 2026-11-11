/**
 * Format an amount into Indian Rupees (INR - ₹) using the Indian numbering system.
 * e.g. 2450 -> "₹2,450", 150000 -> "₹1,50,000"
 */
export const formatINR = (amount, includeDecimals = false) => {
  if (amount === null || amount === undefined || isNaN(amount)) {
    return '₹0';
  }

  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: includeDecimals ? 2 : 0,
    minimumFractionDigits: includeDecimals ? 2 : 0,
  }).format(amount);
};

export default formatINR;
