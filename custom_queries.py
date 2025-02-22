custom_queries = {
    "accounts": '''
        SELECT accounts.id, accounts.name AS account_name, cat.name AS category_name, currency.name As currency_name
        FROM accounts
        JOIN cat ON accounts.cat_id = cat.id
        JOIN currency ON accounts.default_currency_id = currency.id
    '''
}