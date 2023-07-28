[Refer to HaoYi's GitHub for DataVerse for reference i guess](https://github.com/ghy99/DataVerse)

# ckanext-versiontree

This extension allows the rendering of a version tree acquired from ClearML and displaying it on CKAN.

**plugins.py:**

Refer to `plugin.py` for the implementation of the back-end logic.

- This plugin contains the functions for the dataset object from ClearML, fetching the dependency graph of the dataset, sorting dataset IDs, and rendering the version tree with dataset details on the frontend. 
- Additionally, it provides a CKAN plugin class `IBlueprint` to handle configuration and routing.

In this extension, we rendered our own HTML page for the version tree. 

- Refer to the `/templates/` folder for the HTML scripts. 
- Refer to the `/assets/` folder for the CSS and JavaScript scripts. 

```python
plugin.py

    getDependencyGraph(dataset):
        """
        This function gets the dependency graph of the dataset parameter that is passed in and
        returns the dependency graph.
        An error is thrown if the dependency graph cannot be obtained.
        """

    getAllDatasetID(dataset_id):
        """
        This function gets the dataset from the dataset_id passed in and returns the dataset. 
        An errror is thrown if the dataset cannot be obtained.
        """

    sortDataset(dataset_IDs, dataset_details):
        """ 
        This function takes in a list of unsorted dataset IDs and 
        returns a sorted list of the same IDs.
        """

    retrieveDatasetDetails(dataset_details):
        """ 
        This function takes a dataset object with dataset IDs and their attributes as input 
        and returns a condensed dictionary. 
        Each dataset ID is associated with a nested dictionary that includes the project name,
        dataset name, and version, along with their respective values.
        """

    renderVersionTree():
        """
        This function retrieves the specified dataset's object form ClearML and 
        returns the dependency graph, dataset_IDs and the dataset_details through the
        render_template function to display them on the frontend.
        """

   
    get_blueprint(self):
        """ 
        This method under the IBlueprint interface creates a Flask blueprint object that
        associates the "/versiontree" URl path with the renderVersionTree function above.
        """


HTML

    versionTree.html:
        """
        This HTML renders the webpage for the version tree. 
        When the `Render Version Tree` button is clicked, 
        it calls the `debug` function in `versionTree_script.js` in the `/assets` folder.
        It also imports the `d3js` library, as this library is used to generate the version tree.

        It renders its CSS through the `versionTree_style.css` in the `/assets` folder.
        """

JavaScript
    versionTree_script.js:

    function get_nodes_set(dataset_IDs, graphData)
    """
    Description: 
        This function takes two parameters: 
            - dataset_IDs
            - graphData
        It processes the dataset_IDs array and creates a Set containing unique node IDs 
        from the dataset_IDs array and their corresponding parents' IDs from the graphData object.

    Parameters:
        dataset_IDs (Array): 
            An array of dataset IDs.
        graphData (Dict): 
            A dictionary containing information about the relationships between datasets, 
            where the keys are dataset IDs, and the values are arrays of parent dataset IDs.
    
    Returns:
        nodesSet (Set): 
            A Set containing unique node IDs, including dataset IDs and their parents' IDs.
    """

    function get_nodes(nodesSet, height, width)
    """
    Description: 
        This function takes three parameters: 
            - nodesSet
            - height
            - width
        It processes the `nodesSet` Set to create an array of node objects 
        with initial x and y positions for data visualization.

    Parameters:
        nodesSet (Set): 
            A Set containing unique node IDs, including dataset IDs and their parents' IDs.
        height (Number): 
            The height of the visualization area.
        width (Number): 
            The width of the visualization area.

    Returns:
        nodes (Array): 
            An array of node objects with properties id, x, and y 
            representing the node ID and its initial coordinates for data visualization.
    """

    function get_links(graphData, nodes)
    """
    Description: 
        This function takes two parameters: 
            - graphData
            - nodes
        It processes the graphData object to create an array of link objects 
        representing the connections between nodes based on the parent-child relationships.

    Parameters:
        graphData (Object): 
            An object containing information about the relationships between datasets, 
            where the keys are dataset IDs, 
            and the values are arrays of parent dataset IDs.
        nodes (Array): 
            An array of node objects with properties id, x, and y.

    Returns:
        links (Array): An array of link objects with source and target properties representing the connections between nodes for data visualization.
    """

    function get_simulation(nodes, links, height, width)
    """
    Description: 
        This function takes four parameters: 
            - nodes
            - links
            - height
            - width
        It creates a D3.js force simulation with predefined forces 
        (link, charge, center, and collide) for positioning the nodes in the visualization.

    Parameters:
        nodes (Array): 
            An array of node objects with properties id, x, and y.
        links (Array): 
            An array of link objects with source and target properties 
            representing the connections between nodes.
        height (Number): 
            The height of the visualization area.
        width (Number): 
            The width of the visualization area.

    Returns:
        simulation (Object): A D3.js force simulation object configured with the specified forces for node positioning.
    """

    function create_svg_for_links(svg, links)
    """
        Description: 
            This function takes two parameters: 
                - svg
                - links
            It creates SVG line elements representing the links (connections) 
            between nodes and appends them to the provided svg container.

        Parameters:
            svg (Object): 
                A D3.js SVG container element where the links will be appended.
            links (Array): 
                An array of link objects with source and target properties 
                representing the connections between nodes.

        Returns:
            link (Object): 
            A D3.js selection of SVG line elements representing the links between nodes.
    """

    function create_svg_for_nodes(svg, nodes)
    """
        Description: 
            This function takes two parameters: 
                - svg
                - nodes
            It creates SVG g (group) elements representing the nodes
            and appends them to the provided svg container.

        Parameters:
            svg (Object): 
                A D3.js SVG container element where the node groups will be appended.
            nodes (Array): 
                An array of node objects with properties id, x, and y.

        Returns:
            node (Object): 
                A D3.js selection of SVG g (group) elements representing the node groups.
    """

    function get_node_container(dataset_details, node)
    """
        Description: 
            This function takes two parameters: 
                - dataset_details
                - node
            It appends a group container for each node in the provided node selection 
            and adds a rectangle and text containing dataset details inside the container.

        Parameters:
            dataset_details (Object): 
                An object containing details about each dataset, 
                with the dataset ID as the key and dataset information as the value.
            node (Object): 
                A D3.js selection of SVG g (group) elements representing the nodes.

        Returns:
            nodeContainer (Object): 
                A D3.js selection of SVG g (group) elements 
                representing the node containers with the added rectangle and text elements.
    """

    function wrapText(text, width, lineHeight)
    """
        Description: 
            This function is used to wrap text inside an SVG text element to fit 
            within a specified width. 
            It breaks long lines of text into multiple lines and adjusts the position 
            of the text elements to ensure they do not overflow the given width.

        Parameters:
            text (Object): 
                A D3.js selection of SVG text elements to be wrapped.
            width (Number): 
                The maximum width in pixels that the text should occupy before wrapping.
            lineHeight (Number, optional): 
                The desired line height (in em units) for the wrapped text. 
                If not provided, the default value is 1.

        Returns:
            None: 
                It modifies the provided text elements by wrapping the text within
                the specified width and adjusting the y position to create multiline text.

        Note:
            The function assumes that the text content of the text elements contains
            words separated by whitespace (e.g., spaces).
            It calculates the length of each line of text by comparing the computed
            text length with the specified width.
            If a line exceeds the width, it breaks the line and starts a new line 
            with the remaining words.
            The `wrapText` function is used within the `get_node_container` function 
            to format the text inside the SVG rectangle representing each node 
            with dataset details. 
            It helps prevent text overflow and ensures the dataset information fits 
            neatly within the specified width.
    """

    function debug(graphData, dataset_IDs, dataset_details)
    """
        Description: 
            This function is used for debugging purposes and orchestrates the creation 
            of the data visualization. 
                It takes three parameters: 
                    - graphData
                    - dataset_IDs
                    - dataset_details
                and sets up the SVG container, nodes, links, simulation, 
                and node containers for the data visualization.

        Parameters:
            graphData (Object): 
                An object containing information about the relationships between datasets, 
                where the keys are dataset IDs, and the values are arrays of parent dataset IDs.
            dataset_IDs (Array): 
                An array of dataset IDs.
            dataset_details (Object): 
                An object containing details about each dataset, with the dataset ID 
                as the key and dataset information as the value.

        Returns:
            None:
                It sets up the data visualization within the specified SVG container.
        
        Please note that the above documentation describes the purpose and functionality 
        of each function in the provided JavaScript code. 
        The code seems to be using D3.js library for data visualization, 
        and it sets up the nodes, links, and simulation for visualizing the 
        relationships between datasets. 
    """
```

## Installation

1. Create an extension with the following command:
   
   `docker compose -f docker-compose.dev.yml exec ckan-dev /bin/sh -c "ckan generate extension --output-dir /srv/app/src_extensions"`

2. Add your extension name to your .env file. 

   `CKAN__PLUGINS="envvars datastore datapusher versiontree"`

3. Restart CKAN. 

   `docker compose -f docker-compose.dev.yml up --build`


## Config settings

None at present


## Tests

None at present