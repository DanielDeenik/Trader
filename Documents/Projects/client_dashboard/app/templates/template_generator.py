def generate_template(data):
    template = f"Sustainability Report for: {data['client_name']}\n"
    template += "Data points included:\n"
    for point in data['data_points']:
        template += f"- {point}\n"
    return template
