import React from "react";

export default function TaxReceiptCard({ data }: { data: any }) {
  if (!data) return null;

  // Safe currency formatter that handles nulls/undefined gracefully
  const formatPKR = (amount: number | null | undefined) => {
    if (amount === null || amount === undefined) return "PKR 0";
    return new Intl.NumberFormat("en-PK", {
      style: "currency",
      currency: "PKR",
      maximumFractionDigits: 0,
    }).format(amount);
  };

  // Safe bracket formatter
  const renderBracket = () => {
    const lower = formatPKR(data.bracket_lower_bound);
    const upper = data.bracket_upper_bound ? formatPKR(data.bracket_upper_bound) : "No Limit";
    return `${lower} to ${upper}`;
  };

  return (
    <div className="bg-white border border-gray-200 rounded-xl shadow-sm overflow-hidden my-4 max-w-md">
      {/* Header */}
      <div className="bg-slate-50 border-b border-gray-200 px-4 py-3">
        <h3 className="font-semibold text-gray-800 text-sm uppercase tracking-wider">
          Tax Calculation Summary
        </h3>
      </div>

      {/* Body */}
      <div className="p-4 space-y-3 text-sm">
        <div className="flex justify-between items-center border-b border-gray-100 pb-2">
          <span className="text-gray-500">Annual Income</span>
          <span className="font-medium text-gray-800">{formatPKR(data.annual_income)}</span>
        </div>

        <div className="flex justify-between items-center border-b border-gray-100 pb-2">
          <span className="text-gray-500">Tax Bracket Applied</span>
          <span className="font-medium text-gray-800">{renderBracket()}</span>
        </div>

        <div className="flex justify-between items-center border-b border-gray-100 pb-2">
          <span className="text-gray-500">Fixed Tax Amount</span>
          <span className="font-medium text-gray-800">{formatPKR(data.fixed_tax_amount)}</span>
        </div>

        <div className="flex justify-between items-center border-b border-gray-100 pb-2">
          <span className="text-gray-500">Marginal Rate</span>
          <span className="font-medium text-gray-800">{data.marginal_rate}</span>
        </div>

        <div className="flex justify-between items-center border-b border-gray-100 pb-2">
          <span className="text-gray-500">Marginal Tax Amount</span>
          <span className="font-medium text-gray-800">{formatPKR(data.marginal_tax_amount)}</span>
        </div>
      </div>

      {/* Footer / Total */}
      <div className="bg-blue-50 px-4 py-3 border-t border-blue-100 flex justify-between items-center">
        <span className="font-bold text-blue-900">Total Tax Payable</span>
        <span className="font-bold text-red-600 text-lg">{formatPKR(data.total_tax_payable)}</span>
      </div>
    </div>
  );
}