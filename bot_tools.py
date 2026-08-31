import pandas as pd
import plotly.express as px

def calculate_sheet_metric(df: pd.DataFrame, column_name: str, operation: str) -> dict:
    """Calculates spreadsheet metrics on a column in the dataset.

    Args:
        df: Pandas DataFrame containing the dataset.
        column_name: Name of the column to perform calculation on.
        operation: Calculation to perform ('sum', 'mean', 'count', 'min', 'max').
    """
    if column_name not in df.columns:
        return {"error": f"Column '{column_name}' not found in dataset."}

    # Clean numeric columns if strings with currency/commas were passed
    series = df[column_name]
    if series.dtype == 'object':
        try:
            series = series.astype(str).str.replace('$', '', regex=False).str.replace(',', '', regex=False)
            series = pd.to_numeric(series)
        except Exception:
            pass

    op = operation.lower()
    
    if op == "sum":
        val = series.sum()
    elif op in ["mean", "average"]:
        val = series.mean()
    elif op == "count":
        val = series.count()
    elif op == "min":
        val = series.min()
    elif op == "max":
        val = series.max()
    else:
        return {"error": f"Unsupported operation '{operation}'."}

    return {"result": float(val), "column_name": column_name, "operation": op}


def generate_data_visualization(df: pd.DataFrame, chart_type: str, x_axis: str, y_axis: str = None):
    """Creates a Plotly visualization figure based on dataset columns.

    Args:
        df: Pandas DataFrame containing the dataset.
        chart_type: Type of plot ('bar', 'line', 'scatter', 'histogram').
        x_axis: Column name for the x-axis.
        y_axis: Column name for the y-axis (optional for histogram).
    """
    if x_axis not in df.columns:
        raise ValueError(f"Column '{x_axis}' not found in dataset.")
    if y_axis and y_axis not in df.columns:
        raise ValueError(f"Column '{y_axis}' not found in dataset.")

    chart = chart_type.lower()
    
    if chart == "line":
        fig = px.line(df, x=x_axis, y=y_axis, title=f"{y_axis} over {x_axis}")
    elif chart == "bar":
        fig = px.bar(df, x=x_axis, y=y_axis, title=f"{y_axis} by {x_axis}")
    elif chart == "scatter":
        fig = px.scatter(df, x=x_axis, y=y_axis, title=f"{y_axis} vs {x_axis}")
    elif chart == "histogram":
        fig = px.histogram(df, x=x_axis, title=f"Distribution of {x_axis}")
    else:
        # Default fallback to bar chart
        fig = px.bar(df, x=x_axis, y=y_axis, title=f"{y_axis} by {x_axis}")

    return fig