import pandas as pd
import matplotlib.pyplot as plt

def analyze_data():
    # ساخت داده‌های نمونه
    data = {
        'Month': ['Jan', 'Feb', 'Mar', 'Apr', 'May'],
        'Sales': [12000, 18000, 15000, 22000, 19000],
        'Expenses': [8000, 9000, 10000, 11000, 9500]
    }
    
    # ایجاد DataFrame
    df = pd.DataFrame(data)
    
    # محاسبه سود
    df['Profit'] = df['Sales'] - df['Expenses']
    
    # ذخیره به CSV
    df.to_csv('financial_report.csv', index=False)
    
    # ایجاد نمودار
    plt.figure(figsize=(10, 6))
    df.plot(x='Month', y=['Sales', 'Expenses', 'Profit'], kind='bar')
    plt.title('گزارش مالی سالانه')
    plt.ylabel('مقدار (دلار)')
    plt.savefig('financial_chart.png')
    plt.close()
    
    return df

if __name__ == "__main__":
    result = analyze_data()
    print("تحلیل داده تکمیل شد! خروجی‌ها ذخیره شدند.")
    print(result)