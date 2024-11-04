# Visualization Service

            import plotly.express as px

            def create_scatter_plot(df, x_col, y_col, color_col):
                fig = px.scatter(df, x=x_col, y=y_col, color=color_col)
                return fig
            