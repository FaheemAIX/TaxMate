import React from "react";

export default function TaxReceiptCard({ data }: { data: any }) {
  if (!data || Object.keys(data).length === 0) return null;

  // Helper to format numbers to PKR (e.g., 3000000 -> Rs. 3,000,000)
  const formatPKR = (num: any) => {
    if (typeof num === "number") {
      return new Intl.NumberFormat("en-PK", {
        style: "currency",
        currency: "PKR",
        minimumFractionDigits: 0,
        maximumFractionDigits: 0,
      }).format(num);
    }
    return num;
  };

  // Helper to format snake_case backend keys to Title Case (e.g., tax_payable -> Tax Payable)
  const formatLabel = (key: string) => {
    return key
      .split("_")
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
      .join(" ");
  };

  return (
    <div className="mt-4 bg-white border border-gray-200 rounded-xl overflow-hidden shadow-sm max-w-sm">
      {/* Card Header */}
      <div className="bg-slate-50 px-4 py-3 border-b border-gray-200 flex items-center gap-2">
        <svg className="w-5 h-5 text-emerald-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
        </svg>
        <h3 className="font-semibold text-slate-800 text-sm uppercase tracking-wider">
          Calculation Summary
        </h3>
      </div>
      
      {/* Card Body */}
      <div className="p-4 space-y-3">
        {Object.entries(data).map(([key, value]) => {
          // Highlight deduction or tax fields in red, income in black
          const isTax = key.toLowerCase().includes("tax") || key.toLowerCase().includes("payable") || key.toLowerCase().includes("deduction");
          
          return (
            <div key={key} className="flex justify-between items-center py-1 border-b border-gray-50 last:border-0">
              <span className="text-gray-600 text-sm font-medium">{formatLabel(key)}</span>
              <span className={`font-semibold ${isTax ? "text-red-600" : "text-gray-900"}`}>
                {isTax && typeof value === "number" && value > 0 ? "- " : ""}
                {formatPKR(value)}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}