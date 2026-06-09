def recommend_learning(result):

    recommendations = []

    for skill in result.get(
        "missing_mandatory",
        []
    ):

        recommendations.append(

            f"Learn {skill}"

        )

    for cert in result.get(
        "missing_certs",
        []
    ):

        recommendations.append(

            f"Get certification: {cert}"

        )

    return recommendations