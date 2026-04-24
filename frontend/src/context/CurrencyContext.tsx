import { createContext, useContext, useState, type ReactNode } from "react";

const LS_KEY = "expenseiq_currency";

interface CurrencyContextType {
  currencySymbol: string;
  setCurrencySymbol: (symbol: string) => void;
}

const CurrencyContext = createContext<CurrencyContextType>({
  currencySymbol: "$",
  setCurrencySymbol: () => {},
});

export function CurrencyProvider({ children }: { children: ReactNode }) {
  const [currencySymbol, setCurrencySymbolState] = useState<string>(
    () => localStorage.getItem(LS_KEY) ?? "$"
  );

  function setCurrencySymbol(symbol: string) {
    setCurrencySymbolState(symbol);
    localStorage.setItem(LS_KEY, symbol);
  }

  return (
    <CurrencyContext.Provider value={{ currencySymbol, setCurrencySymbol }}>
      {children}
    </CurrencyContext.Provider>
  );
}

export function useCurrency() {
  return useContext(CurrencyContext);
}
