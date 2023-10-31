import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns


FILE = 'output.csv'

data =  pd.read_csv(FILE, sep=',', header=0 )

# Converting Data Types
categorical_cols = ['numero_mesa', 'Local_de_Comicio', 'Comuna_Municipio', 'Seccion', 
                    'Circuito', 'Distrito', 'Pais', 'Ganador', 'Recommendation']

for col in categorical_cols:
    data[col] = data[col].astype('category')

print(data.describe())
# Setting the aesthetic style of the plots
sns.set_style("whitegrid")

# STEP 1 - Distribution of Tables - Anomalous Tables


# Selecting only the vote count columns for each party
parties_votes = data[['UNION POR LA PATRIA - %', 'LA LIBERTAD AVANZA - %', 'JUNTOS POR EL CAMBIO - %', 
                      'HACEMOS POR NUESTRO PAIS - %', 'FRENTE DE IZQUIERDA Y DE TRABAJADORES - UNIDAD - %']]

# Calculating the winning party's vote percentage in each polling station
winning_party_percentage = parties_votes.max(axis=1).replace(0, np.nan)

# Plotting the histogram
plt.figure(figsize=(10, 6))
sns.histplot(winning_party_percentage, bins=50, kde=False, color='skyblue')
plt.title('Distribution of Winning Party Vote Percentage in Polling Stations')
plt.xlabel('Winning Party Vote Percentage')
plt.ylabel('Number of Polling Stations')
plt.grid(True, which='both', linestyle='--', linewidth=0.5)
plt.axvline(.6, color='red', linestyle='--', linewidth=2, label='60% Threshold')
plt.xlim(0, 1)  # Setting x-axis limit to [0, 100] for clarity
plt.legend()
plt.show()

# How many tables are anomalous? Over 60%?

tables_above_60_percent = (winning_party_percentage > 0.6).mean() * 100
print(tables_above_60_percent)


# Distribution of Anomalous Tables
# Step 1: Identify the polling stations with > 60% votes for the winning party
high_preference_tables = data.loc[winning_party_percentage > 0.6]

# Step 2: Find the winning party in each of these polling stations
# This can be done by identifying the party with the maximum percentage of votes in each row
winning_parties = high_preference_tables[['UNION POR LA PATRIA - %', 'LA LIBERTAD AVANZA - %', 
                                          'JUNTOS POR EL CAMBIO - %', 'HACEMOS POR NUESTRO PAIS - %', 
                                          'FRENTE DE IZQUIERDA Y DE TRABAJADORES - UNIDAD - %']].idxmax(axis=1)

# Step 3: Analyze the distribution of winners
winning_parties_distribution = winning_parties.value_counts(normalize=True) * 100
print(winning_parties_distribution)

winning_parties_count = winning_parties.value_counts(normalize=True) * 100
print(winning_parties_distribution)

# Pastel color palette
colors = sns.color_palette('pastel')

# Plotting the pie chart of high preference tables
plt.figure(figsize=(10, 6))
ax = winning_parties_distribution.plot.pie(autopct='%1.1f%%', startangle=90, colors=colors, labels=None)
plt.ylabel('')  # Hide y-axis label
plt.title('Distribution of Winning Parties in Polling Stations with >60% Votes for Winning Party')
plt.legend(labels=winning_parties_distribution.index, title='Parties', bbox_to_anchor=(1, 0, 0.5, 1))
plt.show()

# BAR CHART - TOTAL VOTES > 60%

party_votes_high_preference = high_preference_tables[['UNION POR LA PATRIA', 'LA LIBERTAD AVANZA', 
                                                      'JUNTOS POR EL CAMBIO', 'HACEMOS POR NUESTRO PAIS', 
                                                      'FRENTE DE IZQUIERDA Y DE TRABAJADORES - UNIDAD']]

# Step 2: Sum the votes received by each party
total_votes_per_party = party_votes_high_preference.sum()


# Specifying colors for each party
colors = ['blue', 'purple', 'yellow', 'green', 'red']


# Abbreviating party names
party_abbreviations = ['UxP', 'LLA', 'JxC', 'HxNP', 'FIT-U']

# Step 3: Create the bar chart
plt.figure(figsize=(12, 6))
ax = sns.barplot(x=total_votes_per_party.index, y=total_votes_per_party.values, palette="pastel")
ax.set_title('Votos en mesas anómalas', fontsize=16, pad=20)
ax.set_xlabel('Party', fontsize=14, labelpad=15)
ax.set_ylabel('Total Votes', fontsize=14, labelpad=15)
ax.set_xticklabels(party_abbreviations, fontsize=12)
ax.tick_params(axis='both', labelsize=12)

# Adding the total votes on top of each bar
for p in ax.patches:
    ax.annotate(f'{int(p.get_height())}', (p.get_x() + p.get_width() / 2., p.get_height()),
                ha='center', va='center', fontsize=12, color='black', xytext=(0, 5),
                textcoords='offset points')

sns.despine(left=True, bottom=True)  # Remove borders
plt.tight_layout()
plt.show()


# Histogram of Districts in High Perf Tables

# Step 1: Filter the data to include only the high preference tables
high_preference_tables = data.loc[winning_party_percentage > 0.6]


# Step 2: Group by "Distrito" and sum the votes
votes_by_distrito = high_preference_tables.groupby('Distrito')[['UNION POR LA PATRIA', 'LA LIBERTAD AVANZA', 'JUNTOS POR EL CAMBIO', 
                                                               'HACEMOS POR NUESTRO PAIS', 'FRENTE DE IZQUIERDA Y DE TRABAJADORES - UNIDAD']].sum()


# Calculate the total votes for each "Distrito"
votes_by_distrito['Total Votes'] = votes_by_distrito.sum(axis=1)

votes_by_distrito = votes_by_distrito.sort_values(by='Total Votes', ascending=False)

votes_by_distrito_filtered = votes_by_distrito[votes_by_distrito['Total Votes'] >= 10000]

votes_by_distrito_filtered_sorted = votes_by_distrito_filtered.sort_values(by='Total Votes', ascending=False)


# Step 3: Create a bar chart
# Create a bar chart
plt.figure(figsize=(10, 5))
ax = sns.barplot(x=votes_by_distrito_filtered_sorted.index, y='Total Votes', data=votes_by_distrito_filtered_sorted, palette='pastel')
ax.set_title('Total Votes by Distrito from High Preference Tables (Above 10,000 Votes)', fontsize=14)
ax.set_xlabel('Distrito', fontsize=12)
ax.set_ylabel('Total Votes', fontsize=12)
ax.tick_params(axis='x', rotation=45, labelsize=10)
ax.tick_params(axis='y', labelsize=10)
sns.despine(left=True, bottom=True)
plt.tight_layout()
plt.savefig("total_votes_by_distrito_high_preference_above_10000.png", dpi=300)
plt.show()

## LEGACTY



# Data for parties' votes
parties_votes = data.filter(like='%', axis=1)

# Melting the data for better visualization
parties_votes_melted = parties_votes.melt(var_name='Party', value_name='Percentage of Votes')

# Plotting the distribution of votes
plt.figure(figsize=(14, 6))
ax = sns.boxplot(x='Party', y='Percentage of Votes', data=parties_votes_melted)
ax.set_title('Distribution of Votes for Different Parties')
ax.set_xticklabels(ax.get_xticklabels(), rotation=45, horizontalalignment='right')
plt.show()


# Identifying polling stations where any party received more than 80% of the votes
dominant_votes_filter = (parties_votes > 0.8).any(axis=1)
dominant_votes_data = data[dominant_votes_filter]

# Counting the instances for each party
dominant_votes_count = (parties_votes[dominant_votes_filter] > 0.8).sum()

# Total number of polling stations with dominant votes
total_dominant_votes = dominant_votes_data.shape[0]

# Distribution of dominant votes amongst parties
dominant_votes_distribution = dominant_votes_count / total_dominant_votes * 100

total_dominant_votes, dominant_votes_count, dominant_votes_distribution
