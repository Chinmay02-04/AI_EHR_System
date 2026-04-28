import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split

data = pd.DataFrame({
    "age":[25,45,50,35,60,48,33,55],
    "bp":[120,140,150,130,160,145,135,155],
    "cholesterol":[180,220,240,200,260,230,210,250],
    "disease":[0,1,1,0,1,1,0,1]
})

X = data[["age","bp","cholesterol"]]
y = data["disease"]

model = LogisticRegression()
model.fit(X,y)

def predict_disease(age,bp,chol):
    result = model.predict([[age,bp,chol]])
    return result[0]